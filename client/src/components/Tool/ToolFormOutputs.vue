<script setup lang="ts">
import { watchDebounced } from "@vueuse/core";
import { computed, onMounted, ref } from "vue";

import {
    previewToolOutputs,
    type ToolOutputActions,
    type ToolOutputsPreview,
    type ToolOutputsPreviewRequest,
} from "@/api/tools";
import localize from "@/utils/localization";
import { errorMessageAsString } from "@/utils/simple-error";

import ToolFormOutput from "./ToolFormOutput.vue";
import GAlert from "@/components/BaseComponents/GAlert.vue";
import GBadge from "@/components/BaseComponents/GBadge.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
import GCollapse from "@/components/BaseComponents/GCollapse.vue";
import Heading from "@/components/Common/Heading.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

type OutputActionsByName = Record<string, ToolOutputActions>;

const props = defineProps<{
    /** The tool request the outputs are described for, as the run would submit it. */
    request: ToolOutputsPreviewRequest;
    /** Changes asked for the outputs, by output name. */
    modelValue: OutputActionsByName;
}>();

const emit = defineEmits<{
    (e: "update:modelValue", value: OutputActionsByName): void;
}>();

// Open from the start when a rerun brings changes along, so they can be seen.
const expanded = ref(Object.keys(props.modelValue).length > 0);
const preview = ref<ToolOutputsPreview | null>(null);
const loading = ref(false);
const errorMessage = ref("");

const requestKey = computed(() => JSON.stringify(props.request));
const collapseState = computed(() => (expanded.value ? "open" : "closed"));
const unsupportedReason = computed(() =>
    preview.value && !preview.value.supported ? preview.value.unsupported_reason : null,
);
const outputs = computed(() => (preview.value?.supported ? (preview.value.outputs ?? []) : []));
const jobCountText = computed(() => {
    const jobCount = preview.value?.supported ? preview.value.job_count : 1;
    return jobCount === 1 ? "" : `${localize("Jobs this run creates:")} ${jobCount}`;
});
const changedCount = computed(() => Object.keys(props.modelValue).length);
const changedText = computed(() => `${changedCount.value} ${localize("changed")}`);

let fetchedKey: string | null = null;
let controller: AbortController | null = null;

async function fetchPreview() {
    // Also while closed when there are changes, so changes of outputs the run no longer creates are dropped.
    if ((!expanded.value && changedCount.value === 0) || requestKey.value === fetchedKey) {
        return;
    }
    const key = requestKey.value;
    fetchedKey = key;
    controller?.abort();
    const currentController = new AbortController();
    controller = currentController;
    loading.value = true;
    try {
        const result = await previewToolOutputs(props.request, currentController.signal);
        preview.value = result;
        errorMessage.value = "";
        // The form may have changed while the preview loaded; the next preview decides then.
        if (requestKey.value === key) {
            dropActionsOfMissingOutputs(result);
        }
    } catch (e) {
        if (currentController.signal.aborted) {
            return;
        }
        // Retry once the form changes or the section opens again.
        fetchedKey = null;
        errorMessage.value = errorMessageAsString(e);
    } finally {
        if (controller === currentController) {
            loading.value = false;
        }
    }
}

function dropActionsOfMissingOutputs(result: ToolOutputsPreview) {
    if (!result.supported) {
        return;
    }
    const names = new Set((result.outputs ?? []).map((output) => output.name));
    const kept = Object.fromEntries(Object.entries(props.modelValue).filter(([name]) => names.has(name)));
    if (Object.keys(kept).length !== Object.keys(props.modelValue).length) {
        emit("update:modelValue", kept);
    }
}

function hasChanges(actions: ToolOutputActions) {
    return Boolean(actions.rename || actions.add_tags?.length || actions.remove_tags?.length || actions.hide);
}

function onUpdateOutput(outputName: string, actions: ToolOutputActions) {
    const updated = { ...props.modelValue };
    if (hasChanges(actions)) {
        updated[outputName] = actions;
    } else {
        delete updated[outputName];
    }
    emit("update:modelValue", updated);
}

function onClearChanges() {
    emit("update:modelValue", {});
}

function onToggle() {
    expanded.value = !expanded.value;
    fetchPreview();
}

watchDebounced(requestKey, fetchPreview, { debounce: 300 });

onMounted(fetchPreview);
</script>

<template>
    <div class="tool-form-outputs" data-description="tool form outputs">
        <Heading h3 separator size="sm" :collapse="collapseState" @click="onToggle">
            {{ localize("Outputs") }}
            <GBadge v-if="changedCount" class="ml-1" data-description="outputs changed count">{{ changedText }}</GBadge>
        </Heading>
        <GCollapse v-model="expanded">
            <LoadingSpan v-if="loading && !preview" :message="localize('Finding the outputs of this run')" />
            <GAlert v-else-if="errorMessage" variant="info" data-description="outputs preview error">
                {{ localize("The outputs can be shown once the inputs are complete.") }} {{ errorMessage }}
            </GAlert>
            <GAlert v-else-if="unsupportedReason" variant="info" data-description="outputs preview unsupported">
                {{ unsupportedReason }}
                <div v-if="changedCount" class="mt-2">
                    {{ localize("Changes to the outputs from the earlier run will still be applied.") }}
                    <GButton size="small" data-description="outputs clear changes" @click="onClearChanges">
                        {{ localize("Clear changes") }}
                    </GButton>
                </div>
            </GAlert>
            <div v-else>
                <p v-if="outputs.length" class="text-muted small mb-1">
                    {{
                        localize(
                            "Rename, tag or hide the outputs. In a new name, #{input_name} inserts the name of that input.",
                        )
                    }}
                    {{ jobCountText }}
                </p>
                <p v-if="!outputs.length" class="mb-0" data-description="outputs preview empty">
                    {{ localize("This run creates no outputs with the current settings.") }}
                </p>
                <ToolFormOutput
                    v-for="output in outputs"
                    :key="output.name"
                    :output="output"
                    :actions="props.modelValue[output.name]"
                    @update="onUpdateOutput" />
            </div>
        </GCollapse>
    </div>
</template>

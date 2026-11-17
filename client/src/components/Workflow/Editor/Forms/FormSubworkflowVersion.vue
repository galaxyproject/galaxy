<script setup lang="ts">
import { computed, ref, watch } from "vue";

import { getSubworkflowVersions, type RefactorRequestAction, type SubworkflowVersions } from "@/api/workflows";
import { errorMessageAsString } from "@/utils/simple-error";

import { workflowVersionText } from "./workflowVersionText";

import GButton from "@/components/BaseComponents/GButton.vue";
import GCheckbox from "@/components/BaseComponents/GCheckbox.vue";
import GSelect from "@/components/BaseComponents/GSelect.vue";

const props = defineProps<{
    /** The workflow version the step runs, the step's `content_id` */
    contentId: string;
    stepId: number;
}>();

const emit = defineEmits<{
    (e: "onAttemptRefactor", actions: RefactorRequestAction[]): void;
}>();

const versions = ref<SubworkflowVersions | null>(null);
const loadError = ref<string | null>(null);
const selected = ref<string | null>(null);
const recursive = ref(false);

const currentKey = computed(() => {
    if (!versions.value) {
        return null;
    }
    if (versions.value.trs_version_id) {
        return `trs:${versions.value.trs_version_id}`;
    }
    return `stored:${versions.value.current_version}`;
});

const storedOptions = computed(() => {
    const all = versions.value?.versions ?? [];
    return all.map((version, index) => {
        const markers = [];
        if (version.version === versions.value?.current_version) {
            markers.push("current");
        }
        if (index === all.length - 1) {
            markers.push("newest");
        }
        return { value: `stored:${version.version}`, text: workflowVersionText(version, markers) };
    });
});

const trsOptions = computed(() =>
    (versions.value?.trs_versions ?? []).map((version) => {
        const markers = [];
        if (version.trs_version_id === versions.value?.trs_version_id) {
            markers.push("current");
        }
        if (version.trs_version_id === versions.value?.trs_upgrade_version_id) {
            markers.push("newer");
        }
        const suffix = markers.length ? ` (${markers.join(", ")})` : "";
        return { value: `trs:${version.trs_version_id}`, text: `${version.name}${suffix}` };
    }),
);

/** Nested upgrades only apply to the newest version of a workflow that wasn't imported from TRS. */
const canRecurse = computed(() => {
    const all = versions.value?.versions ?? [];
    const newest = all[all.length - 1];
    return !versions.value?.trs_version_id && newest !== undefined && selected.value === `stored:${newest.version}`;
});

const canSwitch = computed(() => selected.value !== null && selected.value !== currentKey.value);

async function load(contentId: string) {
    loadError.value = null;
    try {
        versions.value = await getSubworkflowVersions(contentId);
        selected.value = currentKey.value;
    } catch (error) {
        versions.value = null;
        loadError.value = errorMessageAsString(error);
    }
}

watch(() => props.contentId, load, { immediate: true });

function onSwitch() {
    const key = selected.value;
    if (!key) {
        return;
    }
    const target = key.startsWith("trs:")
        ? { trs_version_id: key.slice("trs:".length) }
        : { version: parseInt(key.slice("stored:".length), 10) };
    emit("onAttemptRefactor", [
        {
            action_type: "upgrade_subworkflow",
            step: { order_index: props.stepId },
            recursive: canRecurse.value && recursive.value,
            ...target,
        },
    ]);
}
</script>

<template>
    <div class="ui-form-element section-row" data-description="subworkflow version">
        <label class="ui-form-title" :for="`subworkflow-version-${stepId}`">Sub-workflow version</label>
        <div v-if="loadError" class="text-danger">{{ loadError }}</div>
        <div v-else-if="!versions" class="text-muted">Loading versions...</div>
        <template v-else>
            <GSelect :id="`subworkflow-version-${stepId}`" v-model="selected" size="small">
                <optgroup label="Versions of this workflow">
                    <option v-for="option in storedOptions" :key="option.value" :value="option.value">
                        {{ option.text }}
                    </option>
                </optgroup>
                <optgroup v-if="trsOptions.length" label="TRS releases">
                    <option v-for="option in trsOptions" :key="option.value" :value="option.value">
                        {{ option.text }}
                    </option>
                </optgroup>
            </GSelect>
            <div v-if="versions.trs_error" class="text-warning small">
                TRS versions are unavailable: {{ versions.trs_error }}
            </div>
            <GCheckbox v-if="canRecurse" v-model="recursive" class="mt-1">
                Also switch the sub-workflows nested inside it to their newest versions
            </GCheckbox>
            <div class="ui-form-info form-text text-muted">
                Switches which version of the sub-workflow this step runs. The tools inside it keep the versions the
                chosen version uses.
            </div>
            <GButton size="small" class="mt-1" :disabled="!canSwitch" @click="onSwitch">Switch version</GButton>
        </template>
    </div>
</template>

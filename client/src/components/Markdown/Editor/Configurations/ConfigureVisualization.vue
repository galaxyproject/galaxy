<template>
    <BAlert v-if="errorMessage" variant="warning" show>{{ errorMessage }}</BAlert>
    <div v-else class="p-2">
        <ConfigureHeader :has-changed="hasChanged" @ok="onOk" @cancel="$emit('cancel')" />
        <ConfigureSelector
            :labels="labels"
            :object-name="objectName"
            object-type="history_dataset_id"
            @change="onChange" />
        <FormElementLabel title="Height" help="Specify the height of the view in pixel.">
            <FormNumber
                id="visualization-height"
                v-model="height"
                :min="100"
                :max="1000"
                type="integer"
                @input="onHeight" />
        </FormElementLabel>
        <BAlert v-if="warnings.length" variant="warning" show class="mt-2">
            <div>This visualization configuration may have issues:</div>
            <ul class="mb-0">
                <li v-for="(warning, index) in warnings" :key="index">{{ warning }}</li>
            </ul>
        </BAlert>
    </div>
</template>

<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { computed, type Ref, ref, watch } from "vue";

import { fetchPlugin } from "@/api/plugins";
import type { VisualizationEmbedConfig, WorkflowLabel } from "@/components/Markdown/Editor/types";
import { parseBlockContent, serializeBlockContent } from "@/components/Markdown/Utilities/blockContent";
import { validateConfig } from "@/components/Markdown/Utilities/validateConfig";
import type { OptionType } from "@/components/SelectionField/types";

import ConfigureHeader from "./ConfigureHeader.vue";
import ConfigureSelector from "./ConfigureSelector.vue";
import FormNumber from "@/components/Form/Elements/FormNumber.vue";
import FormElementLabel from "@/components/Form/FormElementLabel.vue";

const DEFAULT_HEIGHT = 400;

const props = defineProps<{
    content: string;
    labels?: Array<WorkflowLabel>;
}>();

const emit = defineEmits<{
    (e: "cancel"): void;
    (e: "change", content: string): void;
}>();

const contentObject: Ref<VisualizationEmbedConfig> = ref({});
const errorMessage = ref("");
const hasChanged = ref(false);
const height = ref();
const parametersSchema: Ref<Record<string, unknown> | undefined> = ref();
const warnings: Ref<Array<string>> = ref([]);

const hasLabels = computed(() => props.labels !== undefined);
const objectName = computed(() => contentObject.value.dataset_name || "...");

function onChange(option: OptionType) {
    if (contentObject.value) {
        if (hasLabels.value && option.data && option.data.label) {
            contentObject.value.dataset_label = option.data.label;
            contentObject.value.dataset_id = undefined;
            contentObject.value.dataset_url = undefined;
        } else {
            contentObject.value.dataset_id = option.id;
            contentObject.value.dataset_label = undefined;
            contentObject.value.dataset_url = undefined;
        }
        contentObject.value.dataset_name = option.name;
        hasChanged.value = true;
        revalidate();
    }
}

function onHeight(newHeight: number) {
    contentObject.value.height = newHeight;
    hasChanged.value = true;
    revalidate();
}

function onOk() {
    emit("change", serializeBlockContent(contentObject.value));
}

function revalidate() {
    warnings.value = parametersSchema.value ? validateConfig(parametersSchema.value, contentObject.value) : [];
}

async function loadSchema() {
    const name = contentObject.value.visualization_name;
    if (!name) {
        parametersSchema.value = undefined;
    } else {
        try {
            const plugin = await fetchPlugin(name);
            parametersSchema.value = plugin.parameters_schema;
        } catch {
            parametersSchema.value = undefined;
        }
    }
    revalidate();
}

function parseContent() {
    try {
        contentObject.value = parseBlockContent(props.content) as VisualizationEmbedConfig;
        height.value = contentObject.value.height || DEFAULT_HEIGHT;
        errorMessage.value = "";
        loadSchema();
    } catch (e) {
        errorMessage.value = `Failed to parse: ${e}`;
    }
}

watch(
    () => props.content,
    () => parseContent(),
    { immediate: true },
);
</script>

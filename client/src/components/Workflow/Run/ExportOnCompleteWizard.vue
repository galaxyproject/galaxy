<script setup lang="ts">
import { BButton } from "bootstrap-vue";
import { computed, ref } from "vue";

import type { ModelStoreFormat } from "@/api";
import type { WriteStoreToPayload } from "@/api/exports";
import { useWizard } from "@/components/Common/Wizard/useWizard";
import {
    AVAILABLE_INVOCATION_EXPORT_PLUGINS,
    type InvocationExportPlugin,
} from "@/components/Workflow/Invocation/Export/Plugins";

import ExportFormatSelector from "@/components/Common/ExportFormatSelector.vue";
import ExportIncludeOptions from "@/components/Common/ExportIncludeOptions.vue";
import ExportRemoteSourceSelector from "@/components/Common/ExportRemoteSourceSelector.vue";
import GenericWizard from "@/components/Common/Wizard/GenericWizard.vue";
import FileSourceNameSpan from "@/components/FileSources/FileSourceNameSpan.vue";

interface Props {
    initialConfig?: Partial<WriteStoreToPayload> & { fileName?: string; directory?: string };
}

const props = withDefaults(defineProps<Props>(), {
    initialConfig: () => ({}),
});

const emit = defineEmits<{
    (e: "configured", config: WriteStoreToPayload): void;
    (e: "cancel"): void;
}>();

// Internal state for the wizard UI
const directory = ref(props.initialConfig.directory || "");
const fileName = ref(props.initialConfig.fileName || "galaxy-workflow-export");
const modelStoreFormat = ref<ModelStoreFormat>(props.initialConfig.model_store_format || "rocrate.zip");
const includeFiles = ref(props.initialConfig.include_files ?? true);
const includeHidden = ref(props.initialConfig.include_hidden ?? false);
const includeDeleted = ref(props.initialConfig.include_deleted ?? false);

// Use RO-Crate and default-file plugins for export-on-complete (exclude BCO)
const exportPlugins: InvocationExportPlugin[] = [
    AVAILABLE_INVOCATION_EXPORT_PLUGINS.get("ro-crate")!,
    AVAILABLE_INVOCATION_EXPORT_PLUGINS.get("default-file")!,
];

const selectedPlugin = computed(
    () => exportPlugins.find((p) => p.exportParams.modelStoreFormat === modelStoreFormat.value) || exportPlugins[0],
);

const wizard = useWizard({
    "select-format": {
        label: "Select format",
        instructions: "Choose the export format for your workflow results.",
        isValid: () => true,
        isSkippable: () => false,
    },
    "select-destination": {
        label: "Select destination",
        instructions: "Choose where to export the workflow results when it completes.",
        isValid: () => Boolean(directory.value) && Boolean(fileName.value),
        isSkippable: () => false,
    },
    "configure-options": {
        label: "Options",
        instructions: "Configure export options and review your settings.",
        isValid: () => true,
        isSkippable: () => false,
    },
});

function onSubmit() {
    // Construct full target_uri from directory + filename + format
    const dir = directory.value.endsWith("/") ? directory.value : `${directory.value}/`;
    const fullTargetUri = `${dir}${fileName.value}.${modelStoreFormat.value}`;

    emit("configured", {
        target_uri: fullTargetUri,
        model_store_format: modelStoreFormat.value,
        include_files: includeFiles.value,
        include_hidden: includeHidden.value,
        include_deleted: includeDeleted.value,
    });
}

function onCancel() {
    emit("cancel");
}

function onFormatChange(format: string) {
    modelStoreFormat.value = format as ModelStoreFormat;
}
</script>

<template>
    <div>
        <GenericWizard
            class="export-on-complete-wizard"
            :use="wizard"
            submit-button-label="Save Export Configuration"
            container-component="div"
            @submit="onSubmit">
            <div v-if="wizard.isCurrent('select-format')">
                <ExportFormatSelector
                    :model-value="modelStoreFormat"
                    :plugins="exportPlugins"
                    @update:model-value="onFormatChange" />
            </div>

            <div v-if="wizard.isCurrent('select-destination')">
                <ExportRemoteSourceSelector
                    :directory="directory"
                    :file-name="fileName"
                    :file-extension="modelStoreFormat"
                    resource-name="workflow results"
                    :show-file-name="true"
                    @update:directory="directory = $event"
                    @update:file-name="fileName = $event" />
            </div>

            <div v-if="wizard.isCurrent('configure-options')">
                <ExportIncludeOptions
                    :include-files="includeFiles"
                    :include-deleted="includeDeleted"
                    :include-hidden="includeHidden"
                    @update:include-files="includeFiles = $event"
                    @update:include-deleted="includeDeleted = $event"
                    @update:include-hidden="includeHidden = $event" />

                <hr />

                <div class="summary">
                    <h5>Summary</h5>
                    <div><strong>Format:</strong> {{ selectedPlugin?.title }}</div>
                    <div>
                        <strong>Destination:</strong>
                        <FileSourceNameSpan v-if="directory" :uri="directory" class="text-primary" />
                        <span v-else class="text-muted">Not selected</span>
                    </div>
                    <div v-if="fileName"><strong>File name:</strong> {{ fileName }}.{{ modelStoreFormat }}</div>
                    <div>
                        <strong>Options:</strong>
                        <span v-if="includeFiles">Include files</span>
                        <span v-if="includeHidden">, Include hidden</span>
                        <span v-if="includeDeleted">, Include deleted</span>
                    </div>
                </div>
            </div>
            <template v-slot:cancel-button>
                <BButton variant="secondary" @click="onCancel">Cancel</BButton>
            </template>
        </GenericWizard>
    </div>
</template>

<style scoped lang="scss">
.summary {
    background-color: var(--bs-light);
    padding: 1rem;
    border-radius: 0.25rem;
}
</style>

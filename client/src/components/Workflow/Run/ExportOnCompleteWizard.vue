<script setup lang="ts">
import { BButton, BCard, BCardGroup, BCardTitle, BFormCheckbox, BFormGroup } from "bootstrap-vue";
import { computed, reactive } from "vue";

import { useWizard } from "@/components/Common/Wizard/useWizard";
import { borderVariant } from "@/components/Common/Wizard/utils";
import { useFileSources } from "@/composables/fileSources";
import { useMarkdown } from "@/composables/markdown";

import GenericWizard from "@/components/Common/Wizard/GenericWizard.vue";
import FilesInput from "@/components/FilesDialog/FilesInput.vue";
import FileSourceNameSpan from "@/components/FileSources/FileSourceNameSpan.vue";

const { renderMarkdown } = useMarkdown({ openLinksInNewPage: true });

interface ExportConfig {
    target_uri: string;
    format: string;
    include_files: boolean;
    include_hidden: boolean;
    include_deleted: boolean;
}

interface ExportFormat {
    id: string;
    title: string;
    markdownDescription: string;
}

interface Props {
    initialConfig?: ExportConfig;
}

const props = withDefaults(defineProps<Props>(), {
    initialConfig: () => ({
        target_uri: "",
        format: "rocrate.zip",
        include_files: true,
        include_hidden: false,
        include_deleted: false,
    }),
});

const emit = defineEmits<{
    (e: "configured", config: ExportConfig): void;
    (e: "cancel"): void;
}>();

const { hasWritable: hasWritableFileSources } = useFileSources({ exclude: ["rdm"] });

const exportData = reactive<ExportConfig>({
    target_uri: props.initialConfig.target_uri || "",
    format: props.initialConfig.format || "rocrate.zip",
    include_files: props.initialConfig.include_files ?? true,
    include_hidden: props.initialConfig.include_hidden ?? false,
    include_deleted: props.initialConfig.include_deleted ?? false,
});

const exportFormats: ExportFormat[] = [
    {
        id: "rocrate.zip",
        title: "RO-Crate (ZIP)",
        markdownDescription: `**Research Object Crate (RO-Crate)** is a community standard for packaging research data with their metadata.

This format preserves the complete workflow run including inputs, outputs, and provenance information.`,
    },
    {
        id: "tar.gz",
        title: "Galaxy Archive (tar.gz)",
        markdownDescription: `**Galaxy Archive** format packages the workflow invocation in a compressed tar archive.

This is a simple format suitable for backup and transfer.`,
    },
];

const selectedFormat = computed(() => exportFormats.find((f) => f.id === exportData.format) || exportFormats[0]);

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
        isValid: () => Boolean(exportData.target_uri),
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
    emit("configured", { ...exportData });
}

function onCancel() {
    emit("cancel");
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
                <BCardGroup deck>
                    <BCard
                        v-for="format in exportFormats"
                        :key="format.id"
                        :data-export-format="format.id"
                        class="wizard-selection-card"
                        :border-variant="borderVariant(exportData.format === format.id)"
                        @click="exportData.format = format.id">
                        <BCardTitle>
                            <b>{{ format.title }}</b>
                        </BCardTitle>
                        <div v-html="renderMarkdown(format.markdownDescription)" />
                    </BCard>
                </BCardGroup>
            </div>

            <div v-if="wizard.isCurrent('select-destination')">
                <p v-if="!hasWritableFileSources" class="text-warning">
                    No writable file sources are configured. Please contact your administrator.
                </p>
                <BFormGroup
                    v-else
                    id="fieldset-directory"
                    label="Export destination"
                    label-for="directory"
                    description="Select a remote storage location to export results to when the workflow completes.">
                    <FilesInput
                        id="directory"
                        v-model="exportData.target_uri"
                        mode="directory"
                        :require-writable="true"
                        :filter-options="{ exclude: ['rdm'] }"
                        data-test-id="export-destination-input" />
                </BFormGroup>
            </div>

            <div v-if="wizard.isCurrent('configure-options')">
                <BFormGroup label="Dataset files included in the export:">
                    <BFormCheckbox v-model="exportData.include_files" switch data-test-id="include-files-checkbox">
                        Include Active Files
                    </BFormCheckbox>

                    <BFormCheckbox v-model="exportData.include_deleted" switch data-test-id="include-deleted-checkbox">
                        Include Deleted (not purged)
                    </BFormCheckbox>

                    <BFormCheckbox v-model="exportData.include_hidden" switch data-test-id="include-hidden-checkbox">
                        Include Hidden
                    </BFormCheckbox>
                </BFormGroup>

                <hr />

                <div class="summary">
                    <h5>Summary</h5>
                    <div>
                        <strong>Format:</strong> {{ selectedFormat?.title }}
                    </div>
                    <div>
                        <strong>Destination:</strong>
                        <FileSourceNameSpan v-if="exportData.target_uri" :uri="exportData.target_uri" class="text-primary" />
                        <span v-else class="text-muted">Not selected</span>
                    </div>
                    <div>
                        <strong>Options:</strong>
                        <span v-if="exportData.include_files">Include files</span>
                        <span v-if="exportData.include_hidden">, Include hidden</span>
                        <span v-if="exportData.include_deleted">, Include deleted</span>
                    </div>
                </div>
            </div>
        </GenericWizard>
        <div class="mt-3 text-right">
            <BButton variant="secondary" @click="onCancel">Cancel</BButton>
        </div>
    </div>
</template>

<style scoped lang="scss">
.wizard-selection-card {
    cursor: pointer;
    transition: border-color 0.15s ease-in-out;

    &:hover {
        border-color: var(--bs-primary);
    }
}

.summary {
    background-color: var(--bs-light);
    padding: 1rem;
    border-radius: 0.25rem;
}
</style>

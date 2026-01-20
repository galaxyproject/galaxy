<script setup lang="ts">
import { BButton, BCard, BCardGroup, BCardTitle, BFormCheckbox, BFormGroup, BFormInput } from "bootstrap-vue";
import { computed, ref } from "vue";

import type { FilterFileSourcesOptions } from "@/api/remoteFiles";
import type { components } from "@/api/schema";
import { useWizard } from "@/components/Common/Wizard/useWizard";
import { borderVariant } from "@/components/Common/Wizard/utils";
import { useFileSources } from "@/composables/fileSources";
import { useMarkdown } from "@/composables/markdown";
import localize from "@/utils/localization";

import GenericWizard from "@/components/Common/Wizard/GenericWizard.vue";
import FilesInput from "@/components/FilesDialog/FilesInput.vue";
import FileSourceNameSpan from "@/components/FileSources/FileSourceNameSpan.vue";

const { renderMarkdown } = useMarkdown({ openLinksInNewPage: true });

export type WriteStoreToPayload = components["schemas"]["WriteStoreToPayload"];
type ModelStoreFormat = components["schemas"]["ModelStoreFormat"];

interface ExportFormat {
    id: string;
    title: string;
    markdownDescription: string;
}

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

const defaultExportFilterOptions: FilterFileSourcesOptions = { exclude: ["rdm"] };
const { hasWritable: hasWritableFileSources } = useFileSources(defaultExportFilterOptions);

// Internal state for the wizard UI
const directory = ref(props.initialConfig.directory || "");
const fileName = ref(props.initialConfig.fileName || "galaxy-workflow-export");
const modelStoreFormat = ref<ModelStoreFormat>(props.initialConfig.model_store_format || "rocrate.zip");
const includeFiles = ref(props.initialConfig.include_files ?? true);
const includeHidden = ref(props.initialConfig.include_hidden ?? false);
const includeDeleted = ref(props.initialConfig.include_deleted ?? false);

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

const selectedFormat = computed(() => exportFormats.find((f) => f.id === modelStoreFormat.value) || exportFormats[0]);

const directoryDescription = computed(() => localize("Select a 'repository' to export the workflow results to."));
const nameDescription = computed(() => localize("Give the exported file a name."));

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
                        v-for="fmt in exportFormats"
                        :key="fmt.id"
                        :data-export-format="fmt.id"
                        class="wizard-selection-card"
                        :border-variant="borderVariant(modelStoreFormat === fmt.id)"
                        @click="modelStoreFormat = fmt.id as ModelStoreFormat">
                        <BCardTitle>
                            <b>{{ fmt.title }}</b>
                        </BCardTitle>
                        <div v-html="renderMarkdown(fmt.markdownDescription)" />
                    </BCard>
                </BCardGroup>
            </div>

            <div v-if="wizard.isCurrent('select-destination')">
                <p v-if="!hasWritableFileSources" class="text-warning">
                    No writable file sources are configured. Please contact your administrator.
                </p>
                <template v-else>
                    <BFormGroup
                        id="fieldset-directory"
                        label-for="directory"
                        :description="directoryDescription"
                        class="mt-3">
                        <FilesInput
                            id="directory"
                            v-model="directory"
                            mode="directory"
                            :require-writable="true"
                            :filter-options="defaultExportFilterOptions"
                            data-test-id="export-destination-input" />
                    </BFormGroup>

                    <BFormGroup id="fieldset-name" label-for="name" :description="nameDescription" class="mt-3">
                        <div class="d-flex align-items-center">
                            <BFormInput
                                id="name"
                                v-model="fileName"
                                placeholder="Name"
                                required
                                data-test-id="export-file-name-input" />
                            <span class="ml-2 text-muted">.{{ modelStoreFormat }}</span>
                        </div>
                    </BFormGroup>
                </template>
            </div>

            <div v-if="wizard.isCurrent('configure-options')">
                <BFormGroup label="Dataset files included in the export:">
                    <BFormCheckbox v-model="includeFiles" switch data-test-id="include-files-checkbox">
                        Include Active Files
                    </BFormCheckbox>

                    <BFormCheckbox v-model="includeDeleted" switch data-test-id="include-deleted-checkbox">
                        Include Deleted (not purged)
                    </BFormCheckbox>

                    <BFormCheckbox v-model="includeHidden" switch data-test-id="include-hidden-checkbox">
                        Include Hidden
                    </BFormCheckbox>
                </BFormGroup>

                <hr />

                <div class="summary">
                    <h5>Summary</h5>
                    <div><strong>Format:</strong> {{ selectedFormat?.title }}</div>
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

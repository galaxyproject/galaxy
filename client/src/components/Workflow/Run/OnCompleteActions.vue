<script setup lang="ts">
import { BButton, BFormCheckbox, BFormGroup, BModal } from "bootstrap-vue";
import { computed, reactive, ref, watch } from "vue";

import { useFileSources } from "@/composables/fileSources";

import ExportOnCompleteWizard from "./ExportOnCompleteWizard.vue";
import FormCard from "@/components/Form/FormCard.vue";
import FileSourceNameSpan from "@/components/FileSources/FileSourceNameSpan.vue";

interface ExportConfig {
    target_uri: string;
    format: string;
    include_files: boolean;
    include_hidden: boolean;
    include_deleted: boolean;
}

interface OnCompleteAction {
    send_notification?: Record<string, never>;
    export_to_file_source?: ExportConfig;
}

interface Props {
    modelValue: OnCompleteAction[];
}

const props = defineProps<Props>();
const emit = defineEmits<{
    (e: "update:modelValue", value: OnCompleteAction[]): void;
}>();

const { hasWritable: hasWritableFileSources } = useFileSources({ exclude: ["rdm"] });

const showExportWizard = ref(false);

const state = reactive({
    sendNotification: false,
    exportEnabled: false,
    exportConfig: {
        target_uri: "",
        format: "rocrate.zip",
        include_files: true,
        include_hidden: false,
        include_deleted: false,
    } as ExportConfig,
});

// Initialize state from modelValue
watch(
    () => props.modelValue,
    (newValue) => {
        if (newValue && newValue.length > 0) {
            state.sendNotification = newValue.some((a) => "send_notification" in a);
            const exportAction = newValue.find((a) => "export_to_file_source" in a);
            if (exportAction && exportAction.export_to_file_source) {
                state.exportEnabled = true;
                state.exportConfig = { ...state.exportConfig, ...exportAction.export_to_file_source };
            }
        }
    },
    { immediate: true }
);

// Emit changes when state changes
watch(
    () => [state.sendNotification, state.exportEnabled, state.exportConfig],
    () => {
        emitOnComplete();
    },
    { deep: true }
);

function emitOnComplete() {
    const actions: OnCompleteAction[] = [];
    if (state.sendNotification) {
        actions.push({ send_notification: {} });
    }
    if (state.exportEnabled && state.exportConfig.target_uri) {
        actions.push({ export_to_file_source: { ...state.exportConfig } });
    }
    emit("update:modelValue", actions);
}

function onExportConfigured(config: ExportConfig) {
    state.exportConfig = config;
    state.exportEnabled = true;
    showExportWizard.value = false;
}

function openExportWizard() {
    showExportWizard.value = true;
}

function clearExport() {
    state.exportEnabled = false;
    state.exportConfig = {
        target_uri: "",
        format: "rocrate.zip",
        include_files: true,
        include_hidden: false,
        include_deleted: false,
    };
}

const exportSummary = computed(() => {
    if (!state.exportEnabled || !state.exportConfig.target_uri) {
        return null;
    }
    return state.exportConfig;
});
</script>

<template>
    <FormCard title="Completion Actions">
        <template v-slot:body>
            <p class="text-muted">
                Configure actions to run automatically when this workflow invocation completes.
            </p>

            <BFormGroup>
                <BFormCheckbox v-model="state.sendNotification" switch data-test-id="send-notification-checkbox">
                    <span class="font-weight-bold">Send notification</span>
                    <br />
                    <small class="text-muted">
                        Receive a notification when the workflow completes.
                    </small>
                </BFormCheckbox>
            </BFormGroup>

            <BFormGroup v-if="hasWritableFileSources">
                <div class="d-flex align-items-start">
                    <BFormCheckbox
                        v-model="state.exportEnabled"
                        switch
                        data-test-id="export-enabled-checkbox"
                        :disabled="!state.exportConfig.target_uri">
                        <span class="font-weight-bold">Export results on completion</span>
                        <br />
                        <small class="text-muted">
                            Automatically export the invocation to a remote storage location.
                        </small>
                    </BFormCheckbox>
                </div>

                <div v-if="exportSummary" class="mt-2 ml-4 p-2 border rounded bg-light">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <strong>Export destination:</strong>
                            <FileSourceNameSpan :uri="exportSummary.target_uri" class="text-primary" />
                            <br />
                            <small class="text-muted">
                                Format: {{ exportSummary.format }}
                                <span v-if="exportSummary.include_files">, with files</span>
                            </small>
                        </div>
                        <div>
                            <BButton size="sm" variant="outline-primary" @click="openExportWizard">
                                <span class="fa fa-edit" /> Edit
                            </BButton>
                            <BButton size="sm" variant="outline-danger" class="ml-1" @click="clearExport">
                                <span class="fa fa-times" /> Remove
                            </BButton>
                        </div>
                    </div>
                </div>

                <BButton
                    v-else
                    variant="outline-primary"
                    size="sm"
                    class="mt-2 ml-4"
                    data-test-id="configure-export-button"
                    @click="openExportWizard">
                    <span class="fa fa-cog" /> Configure Export
                </BButton>
            </BFormGroup>

            <BModal
                v-model="showExportWizard"
                title="Configure Completion Export"
                size="lg"
                hide-footer
                data-test-id="export-wizard-modal">
                <ExportOnCompleteWizard
                    :initial-config="state.exportConfig"
                    @configured="onExportConfigured"
                    @cancel="showExportWizard = false" />
            </BModal>
        </template>
    </FormCard>
</template>

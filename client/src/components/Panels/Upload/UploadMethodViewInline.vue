<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, ref, watch } from "vue";

import { useTargetHistoryUploadState } from "@/composables/history/useTargetHistoryUploadState";
import { DEFAULT_ALLOWED_METHODS } from "@/composables/upload/useUploadMethodModal";
import { useUploadSubmission } from "@/composables/upload/useUploadSubmission";
import { useHistoryStore } from "@/stores/historyStore";
import { errorMessageAsString } from "@/utils/simple-error";

import type { UploadMethodComponent, UploadMethodConfig } from "./types";
import { useFilteredUploadMethods } from "./uploadMethodRegistry";
import type { UploadedDataset, UploadModalConfig } from "./uploadModalTypes";

import GButton from "@/components/BaseComponents/GButton.vue";
import GTip from "@/components/BaseComponents/GTip.vue";
import GCard from "@/components/Common/GCard.vue";

interface UploadMethodViewInlineProps {
    config: UploadModalConfig;
    hideTips?: boolean;
}

interface UploadMethodViewInlineEmits {
    (e: "uploaded", datasets: UploadedDataset[]): void;
    (e: "cancelled"): void;
}

const props = withDefaults(defineProps<UploadMethodViewInlineProps>(), {
    hideTips: true,
});

const emit = defineEmits<UploadMethodViewInlineEmits>();

const historyStore = useHistoryStore();
const { currentHistoryId } = storeToRefs(historyStore);

const { submitPreparedUpload } = useUploadSubmission();

const modalConfig = computed<UploadModalConfig>(() => props.config ?? {});
const allowedMethods = computed(() => modalConfig.value.allowedMethods ?? DEFAULT_ALLOWED_METHODS);
const availableMethods = useFilteredUploadMethods(allowedMethods);
const selectedMethod = ref<UploadMethodConfig | null>(null);
const uploadMethodRef = ref<UploadMethodComponent | null>(null);
const canUpload = ref(false);
const uploading = ref(false);
const uploadProgress = ref(0);
const error = ref<string | null>(null);

const effectiveHistoryId = computed(() => modalConfig.value.targetHistoryId ?? currentHistoryId.value ?? "");

const { uploadBlockReason } = useTargetHistoryUploadState(effectiveHistoryId);

const canStartUpload = computed(() => {
    return Boolean(selectedMethod.value) && !uploading.value && canUpload.value && !uploadBlockReason.value;
});

const immediateFiles = computed(() => {
    if (selectedMethod.value?.id !== "local-file") {
        return undefined;
    }
    return modalConfig.value.immediateFiles;
});

const startButtonTitle = computed(() => {
    if (uploadBlockReason.value) {
        return uploadBlockReason.value;
    }
    if (!canUpload.value) {
        return "Configure upload options first";
    }
    return "Start upload";
});

watch(
    () => availableMethods.value,
    (methods) => {
        if (!methods.length) {
            selectedMethod.value = null;
            return;
        }
        if (!selectedMethod.value || !methods.some((method) => method.id === selectedMethod.value?.id)) {
            selectedMethod.value = methods[0] ?? null;
        }
    },
    { immediate: true },
);

function selectMethod(method: UploadMethodConfig) {
    selectedMethod.value = method;
    canUpload.value = false;
    error.value = null;
}

function handleReadyStateChange(ready: boolean) {
    canUpload.value = ready;
}

function handleCancelClick() {
    if (uploading.value) {
        return;
    }
    emit("cancelled");
}

async function handleStartClick() {
    if (!canStartUpload.value) {
        return;
    }

    if (!effectiveHistoryId.value) {
        error.value = "No target history is available for upload.";
        return;
    }

    if (!selectedMethod.value) {
        error.value = "Select an upload method first.";
        return;
    }

    const prepared = uploadMethodRef.value?.prepareUpload();
    if (!prepared) {
        error.value = "This upload method did not return any upload items.";
        return;
    }

    uploadProgress.value = 0;
    uploading.value = true;
    error.value = null;

    try {
        const datasets = await submitPreparedUpload(effectiveHistoryId.value, prepared, (pct) => {
            uploadProgress.value = pct;
        });
        emit("uploaded", datasets);
    } catch (uploadError) {
        error.value = errorMessageAsString(uploadError);
    } finally {
        uploading.value = false;
    }
}
</script>

<template>
    <div class="upload-method-inline-content d-flex flex-column">
        <div class="upload-method-modal-content d-flex flex-grow-1 overflow-hidden">
            <aside class="methods-pane pr-2">
                <div class="methods-scroll pr-1">
                    <GCard
                        v-for="method in availableMethods"
                        :key="method.id"
                        clickable
                        container-class="mt-1 mb-1"
                        :title="method.name"
                        title-size="text"
                        :description="method.description"
                        :title-icon="{ icon: method.icon, class: 'text-primary', size: 'lg' }"
                        :selected="selectedMethod?.id === method.id"
                        :disabled="method.disabled"
                        :disabled-title="method.disabledTitle"
                        :data-method-id="method.id"
                        @click="selectMethod(method)" />
                </div>
            </aside>

            <section class="method-pane d-flex flex-column overflow-hidden">
                <GTip
                    v-if="selectedMethod?.tips && !hideTips"
                    :tips="selectedMethod.tips"
                    variant="info"
                    class="mb-2" />
                <div v-if="error" class="alert alert-danger py-1 px-2 mb-2">
                    {{ error }}
                </div>
                <div v-if="uploading" class="mb-2">
                    <div class="d-flex justify-content-between small text-muted mb-1">
                        <span>Uploading</span>
                        <span>{{ Math.round(uploadProgress) }}%</span>
                    </div>
                    <div class="upload-progress-track">
                        <div class="upload-progress-fill" :style="{ width: `${uploadProgress}%` }"></div>
                    </div>
                </div>
                <div class="method-content overflow-auto">
                    <component
                        :is="selectedMethod?.component"
                        v-if="selectedMethod"
                        ref="uploadMethodRef"
                        :method="selectedMethod"
                        :target-history-id="effectiveHistoryId"
                        :allow-collections="config.allowCollections"
                        :formats="config.formats"
                        :multiple="config.multiple"
                        :initial-files="immediateFiles"
                        :transient="true"
                        @ready="handleReadyStateChange" />
                </div>
            </section>
        </div>

        <div class="upload-method-inline-footer d-flex justify-content-end gap-2 mt-2">
            <GButton
                outline
                color="grey"
                :disabled="uploading"
                data-test-id="upload-method-inline-cancel"
                @click="handleCancelClick"
                >Cancel</GButton
            >
            <GButton
                color="blue"
                :disabled="!canStartUpload"
                :title="startButtonTitle"
                data-test-id="upload-method-inline-start"
                @click="handleStartClick">
                Start
            </GButton>
        </div>
    </div>
</template>

<style scoped lang="scss">
@import "@/style/scss/theme/blue.scss";

.upload-method-inline-content {
    min-height: 500px;
}

.upload-method-modal-content {
    min-height: 0;
}

.methods-pane {
    width: 320px;
    border-right: $border-default;
}

.methods-scroll {
    max-height: 100%;
    overflow: auto;
}

.method-pane {
    min-width: 0;
    flex: 1;
    padding-left: 0.5rem;
}

.method-content {
    min-height: 0;
    flex: 1;
    display: flex;
    flex-direction: column;
}

.upload-progress-track {
    width: 100%;
    height: 0.45rem;
    border-radius: 999px;
    background: $gray-200;
    overflow: hidden;
}

.upload-progress-fill {
    height: 100%;
    background: $brand-primary;
    transition: width 0.2s ease;
}

.gap-2 {
    gap: 0.5rem;
}
</style>

<script setup lang="ts">
import { faUpload } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { storeToRefs } from "pinia";
import { computed, ref, watch } from "vue";

import { useTargetHistoryUploadState } from "@/composables/history/useTargetHistoryUploadState";
import { useUploadSubmission } from "@/composables/upload/useUploadSubmission";
import { useHistoryStore } from "@/stores/historyStore";
import { errorMessageAsString } from "@/utils/simple-error";

import type { UploadMethodComponent, UploadMethodConfig } from "./types";
import { useFilteredUploadMethods } from "./uploadMethodRegistry";
import type { UploadedDataset, UploadModalConfig } from "./uploadModalTypes";

import GButton from "@/components/BaseComponents/GButton.vue";
import GModal from "@/components/BaseComponents/GModal.vue";
import GTip from "@/components/BaseComponents/GTip.vue";
import GCard from "@/components/Common/GCard.vue";
import Heading from "@/components/Common/Heading.vue";

interface UploadMethodModalProps {
    config: UploadModalConfig;
    show: boolean;
    hideTips?: boolean;
}

interface UploadMethodModalEmits {
    (e: "update:show", show: boolean): void;
    (e: "uploaded", datasets: UploadedDataset[]): void;
    (e: "cancelled"): void;
}

const props = defineProps<UploadMethodModalProps>();
const emit = defineEmits<UploadMethodModalEmits>();

const historyStore = useHistoryStore();
const { currentHistoryId } = storeToRefs(historyStore);

const { submitPreparedUpload } = useUploadSubmission();

const modalConfig = computed<UploadModalConfig>(() => props.config ?? {});
const availableMethods = useFilteredUploadMethods(modalConfig);
const selectedMethod = ref<UploadMethodConfig | null>(null);
const uploadMethodRef = ref<UploadMethodComponent | null>(null);
const canUpload = ref(false);
const uploading = ref(false);
const uploadProgress = ref(0);
const error = ref<string | null>(null);
const completed = ref(false);
const cancelled = ref(false);

const effectiveHistoryId = computed(() => modalConfig.value.targetHistoryId ?? currentHistoryId.value ?? "");
const targetHistoryName = computed(() => {
    if (!effectiveHistoryId.value) {
        return null;
    }
    const name = historyStore.getHistoryNameById(effectiveHistoryId.value);
    return name === "..." ? null : name;
});

const title = computed(() => {
    if (modalConfig.value.title) {
        return modalConfig.value.title;
    }
    return modalConfig.value.multiple
        ? "Upload datasets to current history"
        : "Upload a single dataset to current history";
});

const { uploadBlockReason } = useTargetHistoryUploadState(effectiveHistoryId);

const canStartUpload = computed(() => {
    return Boolean(selectedMethod.value) && !uploading.value && canUpload.value && !uploadBlockReason.value;
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

watch(
    () => props.show,
    (newShow) => {
        if (newShow) {
            completed.value = false;
            cancelled.value = false;
            uploading.value = false;
            uploadProgress.value = 0;
            error.value = null;
            uploadMethodRef.value?.reset?.();
        }
    },
);

function selectMethod(method: UploadMethodConfig) {
    selectedMethod.value = method;
    canUpload.value = false;
    error.value = null;
}

function handleReadyStateChange(ready: boolean) {
    canUpload.value = ready;
}

function closeModal() {
    emit("update:show", false);
}

function handleShowUpdate(value: boolean) {
    emit("update:show", value);
}

function handleCancelClick() {
    if (uploading.value) {
        return;
    }
    cancelled.value = true;
    emit("cancelled");
    closeModal();
}

function handleModalClosed() {
    if (!completed.value && !cancelled.value) {
        emit("cancelled");
    }
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
        completed.value = true;
        emit("uploaded", datasets);
        closeModal();
    } catch (uploadError) {
        error.value = errorMessageAsString(uploadError);
    } finally {
        uploading.value = false;
    }
}
</script>

<template>
    <GModal :show="show" size="large" fixed-height footer @update:show="handleShowUpdate" @cancel="handleModalClosed">
        <template v-slot:header>
            <Heading h2 separator size="lg" class="g-modal-title mb-0">
                <FontAwesomeIcon :icon="faUpload" />
                {{ title }}
                <template v-if="targetHistoryName">
                    — <strong>{{ targetHistoryName }}</strong>
                </template>
            </Heading>
        </template>
        <div class="upload-method-modal h-100 d-flex flex-column">
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
                            :transient="true"
                            @ready="handleReadyStateChange" />
                    </div>
                </section>
            </div>
        </div>

        <template v-slot:footer>
            <div class="d-flex justify-content-end gap-2 w-100">
                <GButton outline color="grey" :disabled="uploading" @click="handleCancelClick">Cancel</GButton>
                <GButton
                    color="blue"
                    :disabled="!canStartUpload"
                    :title="startButtonTitle"
                    data-test-id="upload-method-modal-start"
                    @click="handleStartClick">
                    Start
                </GButton>
            </div>
        </template>
    </GModal>
</template>

<style scoped lang="scss">
@import "@/style/scss/theme/blue.scss";

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

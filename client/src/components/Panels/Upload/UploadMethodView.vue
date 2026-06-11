<script setup lang="ts">
import { BFormCheckbox } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router/composables";

import { useTargetHistoryUploadState } from "@/composables/history/useTargetHistoryUploadState";
import { useUploadAdvancedMode } from "@/composables/upload/uploadAdvancedMode";
import { usePrivateObjectStoreConfirmation } from "@/composables/upload/usePrivateObjectStoreConfirmation";
import { useTargetObjectStoreSelectionState } from "@/composables/upload/useTargetObjectStoreSelectionState";
import { useUploadSubmission } from "@/composables/upload/useUploadSubmission";
import { useHistoryStore } from "@/stores/historyStore";
import { useObjectStoreStore } from "@/stores/objectStoreStore";

import type { UploadMethod, UploadMethodComponent } from "./types";
import { getUploadRootBreadcrumb } from "./uploadBreadcrumb";
import { getUploadMethod } from "./uploadMethodRegistry";

import GAlert from "@/components/BaseComponents/GAlert.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
import GTip from "@/components/BaseComponents/GTip.vue";
import BreadcrumbHeading from "@/components/Common/BreadcrumbHeading.vue";
import TargetHistorySelector from "@/components/History/TargetHistorySelector.vue";
import TargetObjectStoreSelector from "@/components/History/TargetObjectStoreSelector.vue";

interface Props {
    methodId: UploadMethod;
}

const props = defineProps<Props>();

const router = useRouter();
const uploadMethodRef = ref<UploadMethodComponent | null>(null);
const canUpload = ref(false);

const { submitPreparedUpload } = useUploadSubmission();

const historyStore = useHistoryStore();
const { currentHistoryId } = storeToRefs(historyStore);

const { advancedMode } = useUploadAdvancedMode();

const targetHistoryId = ref<string>(currentHistoryId.value || "");

const objectStoreStore = useObjectStoreStore();
const { selectableObjectStores } = storeToRefs(objectStoreStore);

const {
    targetObjectStoreId,
    shouldShowObjectStoreSelector,
    objectStoreUploadBlockReason,
    objectStoreDisabledReason,
    handleObjectStoreSelected,
} = useTargetObjectStoreSelectionState(
    targetHistoryId,
    computed(() => advancedMode.value),
);

const { warningMessage: objectStoreWarningMessage, handlePrivateStoreSelection } = usePrivateObjectStoreConfirmation();

// Keep targetHistoryId in sync with currentHistoryId
watch(
    currentHistoryId,
    (newHistoryId) => {
        if (newHistoryId && !targetHistoryId.value) {
            targetHistoryId.value = newHistoryId;
        }
    },
    { immediate: true },
);

const method = computed(() => {
    return props.methodId ? getUploadMethod(props.methodId) : null;
});

const { uploadBlockReason, warningMessage } = useTargetHistoryUploadState(computed(() => targetHistoryId.value));

const canStartUpload = computed(
    () => !uploadBlockReason.value && !objectStoreUploadBlockReason.value && canUpload.value,
);

const startButtonTitle = computed(() => {
    if (uploadBlockReason.value) {
        return warningMessage.value;
    }
    if (objectStoreUploadBlockReason.value) {
        return objectStoreUploadBlockReason.value;
    }
    return canUpload.value ? "Start uploading to Galaxy" : "Configure upload options first";
});

const breadcrumbItems = computed(() => {
    if (!method.value) {
        return [getUploadRootBreadcrumb()];
    }
    return [getUploadRootBreadcrumb("/upload"), { title: method.value.name }];
});

function handleHistorySelected(history: { id: string }) {
    targetHistoryId.value = history.id;
}

async function handleObjectStoreSelection(selection: { object_store_id: string | null; private: boolean }) {
    const selectedStore = selection.object_store_id
        ? selectableObjectStores.value?.find((store) => store.object_store_id === selection.object_store_id)
        : null;

    handleObjectStoreSelected(selectedStore ?? null);
    await handlePrivateStoreSelection(selectedStore ?? null, targetHistoryId.value);
}

function handleCancel() {
    router.push("/upload");
}

function handleStart() {
    if (!canStartUpload.value) {
        return;
    }
    const prepared = uploadMethodRef.value?.prepareUpload();
    if (!prepared) {
        return;
    }
    // Fire-and-forget: progress is tracked in uploadState, visible in the progress view
    void submitPreparedUpload(targetHistoryId.value, prepared, undefined, targetObjectStoreId.value ?? undefined);
    uploadMethodRef.value?.reset?.();
    router.push("/upload/progress");
}

function handleReadyStateChange(ready: boolean) {
    canUpload.value = ready;
}
</script>

<template>
    <div class="upload-method-view d-flex flex-column h-100">
        <BreadcrumbHeading :items="breadcrumbItems">
            <BFormCheckbox
                v-model="advancedMode"
                v-g-tooltip.hover
                data-test-id="upload-advanced-mode-toggle"
                switch
                class="ml-auto align-self-center"
                title="Show advanced upload options">
                <span>Advanced</span>
            </BFormCheckbox>
        </BreadcrumbHeading>

        <div v-if="method" class="upload-method-content flex-grow-1 d-flex flex-column overflow-hidden">
            <GTip v-if="method.tips" :tips="method.tips" variant="info" class="mb-1" />

            <!-- Target History Display -->
            <div v-if="method.requiresTargetHistory" class="target-history-banner px-3 py-2">
                <div class="target-destination-grid">
                    <div class="target-destination-item">
                        <TargetHistorySelector
                            :target-history-id="targetHistoryId"
                            history-caption="Target history"
                            change-link-text="Choose another"
                            change-link-tooltip="Change target history for this upload"
                            modal-title="Select a history for upload"
                            @select-history="handleHistorySelected" />
                    </div>
                    <div v-if="shouldShowObjectStoreSelector" class="target-destination-item">
                        <TargetObjectStoreSelector
                            class="ml-4"
                            :target-object-store-id="targetObjectStoreId"
                            :target-history-id="targetHistoryId"
                            store-caption="Target storage"
                            change-link-tooltip="Change storage location for this upload"
                            :disabled="!!objectStoreDisabledReason"
                            :disabled-message="objectStoreDisabledReason"
                            @select-store="handleObjectStoreSelection" />
                    </div>
                </div>

                <GAlert v-if="objectStoreWarningMessage" show variant="warning" class="mb-0 mt-2 py-1">
                    {{ objectStoreWarningMessage }}
                </GAlert>
            </div>

            <!-- Upload Method Content (scrollable) -->
            <div class="flex-grow-1 overflow-auto p-1">
                <component
                    :is="method.component"
                    ref="uploadMethodRef"
                    :method="method"
                    :target-history-id="targetHistoryId"
                    :target-object-store-id="targetObjectStoreId"
                    @ready="handleReadyStateChange" />
            </div>
        </div>
        <div v-else class="flex-grow-1 text-center text-muted py-5">
            <p>Loading...</p>
        </div>

        <!-- Fixed Footer -->
        <div v-if="method" class="upload-footer">
            <div class="d-flex justify-content-end gap-2">
                <GButton outline color="grey" title="Cancel and return to import methods" @click="handleCancel">
                    <span v-localize>Cancel</span>
                </GButton>
                <GButton
                    v-if="method.showStartButton !== false"
                    color="blue"
                    :disabled="!canStartUpload"
                    :title="startButtonTitle"
                    data-test-id="start-upload"
                    @click="handleStart">
                    <span v-localize>Start</span>
                </GButton>
            </div>
        </div>
    </div>
</template>

<style scoped lang="scss">
@import "@/style/scss/theme/blue.scss";

.upload-method-view {
    background-color: $white;
}

.target-history-banner {
    background-color: $gray-100;
    border-bottom: 1px solid $border-color;
    flex-shrink: 0;
}

.target-destination-grid {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
}

.target-destination-item {
    flex: 1 1 22rem;
    min-width: min(100%, 18rem);
}

@media (max-width: 768px) {
    .target-destination-item {
        flex-basis: 100%;
        min-width: 0;
    }
}

.target-history-name {
    color: $brand-primary;
    font-size: 1rem;
}

.upload-footer {
    flex-shrink: 0;
    padding: 1rem;
    background-color: $white;
    border-top: 1px solid $border-color;
    box-shadow: 0 -2px 4px rgba(0, 0, 0, 0.05);
}

.gap-2 {
    gap: 0.5rem;
}
</style>

<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router/composables";

import { useHistoryStore } from "@/stores/historyStore";

import type { UploadMethod, UploadMethodComponent } from "./types";
import { getUploadRootBreadcrumb } from "./uploadBreadcrumb";
import { getUploadMethod } from "./uploadMethodRegistry";

import GButton from "@/components/BaseComponents/GButton.vue";
import GTip from "@/components/BaseComponents/GTip.vue";
import BreadcrumbHeading from "@/components/Common/BreadcrumbHeading.vue";
import TargetHistorySelector from "@/components/History/TargetHistorySelector.vue";

interface Props {
    methodId: UploadMethod;
}

const props = defineProps<Props>();

const router = useRouter();
const uploadMethodRef = ref<UploadMethodComponent | null>(null);
const canUpload = ref(false);

const historyStore = useHistoryStore();
const { currentHistoryId } = storeToRefs(historyStore);

const targetHistoryId = ref<string>(currentHistoryId.value || "");

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

const breadcrumbItems = computed(() => {
    if (!method.value) {
        return [getUploadRootBreadcrumb()];
    }
    return [getUploadRootBreadcrumb("/upload"), { title: method.value.name }];
});

function handleHistorySelected(history: { id: string }) {
    targetHistoryId.value = history.id;
}

function handleCancel() {
    router.push("/upload");
}

function handleStart() {
    uploadMethodRef.value?.startUpload();
    router.push("/upload/progress");
}

function handleReadyStateChange(ready: boolean) {
    canUpload.value = ready;
}
</script>

<template>
    <div class="upload-method-view d-flex flex-column h-100">
        <BreadcrumbHeading :items="breadcrumbItems" />

        <div v-if="method" class="upload-method-content flex-grow-1 d-flex flex-column overflow-hidden">
            <GTip v-if="method.tips" :tips="method.tips" variant="info" class="mb-1" />

            <!-- Target History Display -->
            <div v-if="method.requiresTargetHistory" class="target-history-banner px-3 py-2">
                <TargetHistorySelector
                    :target-history-id="targetHistoryId"
                    history-caption="Target history"
                    change-link-text="Choose another"
                    change-link-tooltip="Change target history for this upload"
                    modal-title="Select a history for upload"
                    @select-history="handleHistorySelected" />
            </div>

            <!-- Upload Method Content (scrollable) -->
            <div class="flex-grow-1 overflow-auto p-1">
                <component
                    :is="method.component"
                    ref="uploadMethodRef"
                    :method="method"
                    :target-history-id="targetHistoryId"
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
                    :disabled="!canUpload"
                    :title="canUpload ? 'Start uploading to Galaxy' : 'Configure upload options first'"
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

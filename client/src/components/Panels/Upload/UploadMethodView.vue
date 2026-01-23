<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router/composables";

import { useHistoryStore } from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";

import type { UploadMethod, UploadMethodComponent } from "./types";
import { getUploadRootBreadcrumb } from "./uploadBreadcrumb";
import { getUploadMethod } from "./uploadMethodRegistry";

import GButton from "@/components/BaseComponents/GButton.vue";
import BreadcrumbHeading from "@/components/Common/BreadcrumbHeading.vue";
import SelectorModal from "@/components/History/Modals/SelectorModal.vue";

interface Props {
    methodId: UploadMethod;
}

const props = defineProps<Props>();

const router = useRouter();
const showHistorySelector = ref(false);
const uploadMethodRef = ref<UploadMethodComponent | null>(null);
const canUpload = ref(false);

const historyStore = useHistoryStore();
const { currentHistoryId, histories } = storeToRefs(historyStore);

const userStore = useUserStore();
const { isAnonymous } = storeToRefs(userStore);

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

const targetHistoryName = computed(() => {
    return targetHistoryId.value ? historyStore.getHistoryNameById(targetHistoryId.value) : undefined;
});

const method = computed(() => {
    return props.methodId ? getUploadMethod(props.methodId) : null;
});

const breadcrumbItems = computed(() => {
    if (!method.value) {
        return [getUploadRootBreadcrumb()];
    }
    return [getUploadRootBreadcrumb("/upload"), { title: method.value.name }];
});

function openHistorySelector() {
    showHistorySelector.value = true;
}

function handleHistorySelected(history: { id: string }) {
    targetHistoryId.value = history.id;
    showHistorySelector.value = false;
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
            <p class="text-muted mb-3">{{ method.description }}</p>

            <!-- Target History Display -->
            <div v-if="method.requiresTargetHistory" class="target-history-banner px-3 py-2">
                <div class="d-flex align-items-center">
                    <span class="text-muted mr-2" title="This is the history where your uploaded data will go">
                        Destination history:
                    </span>
                    <strong class="target-history-name">{{ targetHistoryName || "selected history" }}</strong>
                    <a
                        v-if="!isAnonymous"
                        href="#"
                        class="change-history-link ml-2"
                        title="Change target history for this upload"
                        @click.prevent="openHistorySelector">
                        change
                    </a>
                </div>
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
                    color="blue"
                    :disabled="!canUpload"
                    :title="canUpload ? 'Start uploading to Galaxy' : 'Configure upload options first'"
                    @click="handleStart">
                    <span v-localize>Start</span>
                </GButton>
            </div>
        </div>

        <SelectorModal
            v-if="method && method.requiresTargetHistory"
            :histories="histories"
            :show-modal.sync="showHistorySelector"
            title="Select a history for upload"
            @selectHistory="handleHistorySelected" />
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

.change-history-link {
    font-size: 0.75rem;

    &:hover {
        text-decoration: underline;
        color: $brand-primary;
    }
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

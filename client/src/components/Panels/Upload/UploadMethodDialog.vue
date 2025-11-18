<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { storeToRefs } from "pinia";
import { computed, ref, watch } from "vue";

import { useHistoryStore } from "@/stores/historyStore";

import type { UploadMode, UploadResult } from "./types";
import { getUploadMethod } from "./uploadMethodRegistry";

import GModal from "@/components/BaseComponents/GModal.vue";
import Heading from "@/components/Common/Heading.vue";
import SelectorModal from "@/components/History/Modals/SelectorModal.vue";

interface Props {
    methodId: UploadMode | null;
    show: boolean;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "update:show", value: boolean): void;
    (e: "close"): void;
    (e: "upload-complete", result: UploadResult): void;
}>();

const isProcessing = ref(false);
const showHistorySelector = ref(false);

const historyStore = useHistoryStore();
const { currentHistoryId, histories } = storeToRefs(historyStore);

const currentHistoryName = computed(() => {
    return currentHistoryId.value ? historyStore.getHistoryNameById(currentHistoryId.value) : undefined;
});

const modalShow = computed({
    get: () => props.show,
    set: (value: boolean) => emit("update:show", value),
});

watch(
    () => props.show,
    (newValue) => {
        if (!newValue) {
            emit("close");
        }
    },
);

const method = computed(() => {
    return props.methodId ? getUploadMethod(props.methodId) : null;
});

function handleUploadStart() {
    isProcessing.value = true;
}

function handleUploadComplete(result: UploadResult) {
    isProcessing.value = false;
    emit("upload-complete", result);
    if (result.success) {
        // Close dialog after successful upload
        modalShow.value = false;
    }
}

function handleUploadError(error: Error | string) {
    isProcessing.value = false;
    console.error("Upload error:", error);
}

function openHistorySelector() {
    showHistorySelector.value = true;
}

function handleHistorySelected(history: { id: string }) {
    // TODO: Change upload target history instead of current history?
    historyStore.setCurrentHistory(history.id);
    showHistorySelector.value = false;
}
</script>

<template>
    <GModal :show.sync="modalShow" fullscreen>
        <template v-slot:header>
            <Heading v-if="method" h2 class="m-0 g-modal-title">
                <FontAwesomeIcon :icon="method.icon" class="mr-2" />
                {{ method.headerAction }}
                <span v-if="method.isUploadToHistory">
                    to <strong>{{ currentHistoryName || "current history" }}</strong>
                    <a
                        title="Selecting a different history will set that history as your current one"
                        href="#"
                        class="select-history-link"
                        @click.prevent="openHistorySelector">
                        or select another
                    </a>
                </span>
            </Heading>
            <Heading v-else h2 class="m-0 g-modal-title"> Import Data </Heading>
        </template>
        <div v-if="method" class="upload-method-content">
            <p class="text-muted mb-2">{{ method.description }}</p>

            <!-- Dynamic component rendering -->
            <component
                :is="method.component"
                :method="method"
                @upload-start="handleUploadStart"
                @upload-complete="handleUploadComplete"
                @upload-error="handleUploadError" />
        </div>
        <div v-else class="text-center text-muted py-5">
            <p>Loading...</p>
        </div>

        <!-- History Selector Modal -->
        <SelectorModal
            v-if="method && method.isUploadToHistory"
            :histories="histories"
            :show-modal.sync="showHistorySelector"
            title="Select a history for upload"
            @selectHistory="handleHistorySelected" />
    </GModal>
</template>

<style scoped lang="scss">
.upload-method-content {
    display: flex;
    flex-direction: column;
    height: 100%;
    overflow: hidden;
}

.select-history-link {
    font-size: 0.6em;
    font-weight: normal;
    text-decoration: none;

    &:hover {
        text-decoration: underline;
    }
}
</style>

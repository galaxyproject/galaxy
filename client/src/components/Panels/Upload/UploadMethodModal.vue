<script setup lang="ts">
import { faUpload } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { storeToRefs } from "pinia";
import { computed, ref, watch } from "vue";

import { useHistoryStore } from "@/stores/historyStore";

import type { UploadedDataset, UploadModalConfig } from "./uploadModalTypes";

import UploadMethodViewInline from "./UploadMethodViewInline.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
import GModal from "@/components/BaseComponents/GModal.vue";
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

const completed = ref(false);
const cancelled = ref(false);

const modalConfig = computed<UploadModalConfig>(() => props.config ?? {});

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

function handleShowUpdate(value: boolean) {
    emit("update:show", value);
}

function handleUploaded(datasets: UploadedDataset[]) {
    completed.value = true;
    emit("uploaded", datasets);
    emit("update:show", false);
}

function handleCancelled() {
    cancelled.value = true;
    emit("cancelled");
    emit("update:show", false);
}

function handleModalClosed() {
    if (!completed.value && !cancelled.value) {
        emit("cancelled");
    }
}

watch(
    () => props.show,
    (show) => {
        if (show) {
            completed.value = false;
            cancelled.value = false;
        }
    },
);
</script>

<template>
    <GModal :show="show" size="large" fixed-height @update:show="handleShowUpdate" @cancel="handleModalClosed">
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
            <UploadMethodViewInline
                v-if="show"
                :key="`${effectiveHistoryId}-${modalConfig.formats}`"
                :config="config"
                :hide-tips="hideTips"
                @uploaded="handleUploaded"
                @cancelled="handleCancelled" />
        </div>
        <template v-slot:footer>
            <div class="d-flex justify-content-end gap-2 w-100">
                <GButton outline color="grey" @click="handleCancelled">Cancel</GButton>
            </div>
        </template>
    </GModal>
</template>

<style scoped lang="scss">
.upload-method-modal {
    min-height: 500px;
}

.gap-2 {
    gap: 0.5rem;
}
</style>

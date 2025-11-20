<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { storeToRefs } from "pinia";
import { computed, ref, watch } from "vue";

import { useHistoryStore } from "@/stores/historyStore";

import type { UploadMode } from "./types";
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
}>();

const showHistorySelector = ref(false);

const historyStore = useHistoryStore();
const { currentHistoryId, histories } = storeToRefs(historyStore);

const targetHistoryId = ref<string>(currentHistoryId.value || "");

const targetHistoryName = computed(() => {
    return targetHistoryId.value ? historyStore.getHistoryNameById(targetHistoryId.value) : undefined;
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
    modalShow.value = false;
}

function handleUploadCancel() {
    modalShow.value = false;
}

function openHistorySelector() {
    showHistorySelector.value = true;
}

function handleHistorySelected(history: { id: string }) {
    targetHistoryId.value = history.id;
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
                    to <strong>{{ targetHistoryName || "selected history" }}</strong>
                    <a
                        title="Choose a different target history for this upload"
                        href="#"
                        class="select-history-link"
                        @click.prevent="openHistorySelector">
                        change
                    </a>
                </span>
            </Heading>
            <Heading v-else h2 class="m-0 g-modal-title"> Import Data </Heading>
        </template>
        <div v-if="method" class="upload-method-content">
            <p class="text-muted mb-2">{{ method.description }}</p>
            <component
                :is="method.component"
                :method="method"
                :target-history-id="targetHistoryId"
                @upload-start="handleUploadStart"
                @cancel="handleUploadCancel" />
        </div>
        <div v-else class="text-center text-muted py-5">
            <p>Loading...</p>
        </div>
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
    margin-left: 0.25em;

    &:hover {
        text-decoration: underline;
    }
}
</style>

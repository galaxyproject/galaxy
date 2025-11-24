<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";
import { useRouter } from "vue-router/composables";

import { useHistoryStore } from "@/stores/historyStore";

import type { UploadMode } from "./types";
import { getUploadMethod } from "./uploadMethodRegistry";

import Heading from "@/components/Common/Heading.vue";
import SelectorModal from "@/components/History/Modals/SelectorModal.vue";

interface Props {
    methodId: UploadMode;
}

const props = defineProps<Props>();

const router = useRouter();
const showHistorySelector = ref(false);

const historyStore = useHistoryStore();
const { currentHistoryId, histories } = storeToRefs(historyStore);

const targetHistoryId = ref<string>(currentHistoryId.value || "");

const targetHistoryName = computed(() => {
    return targetHistoryId.value ? historyStore.getHistoryNameById(targetHistoryId.value) : undefined;
});

const method = computed(() => {
    return props.methodId ? getUploadMethod(props.methodId) : null;
});

function handleUploadStart() {
    // TODO: Display upload progress?
}

function handleUploadCancel() {
    router.back();
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
    <div class="upload-method-view h-100 d-flex flex-column overflow-hidden">
        <div class="header p-3 border-bottom">
            <Heading v-if="method" h2 class="m-0">
                <FontAwesomeIcon :icon="method.icon" class="mr-2" />
                {{ method.headerAction }}
                <span v-if="method.requiresTargetHistory">
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
            <Heading v-else h2 class="m-0"> Import Data </Heading>
        </div>

        <div v-if="method" class="upload-method-content p-3 flex-grow-1 overflow-auto">
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
            v-if="method && method.requiresTargetHistory"
            :histories="histories"
            :show-modal.sync="showHistorySelector"
            title="Select a history for upload"
            @selectHistory="handleHistorySelected" />
    </div>
</template>

<style scoped lang="scss">
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

<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";

import { useTargetHistoryUploadState } from "@/composables/history/useTargetHistoryUploadState";
import { useHistoryStore } from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";

import SelectorModal from "@/components/History/Modals/SelectorModal.vue";
import TargetHistoryLink from "@/components/History/TargetHistoryLink.vue";

interface Props {
    targetHistoryId: string;
    historyCaption?: string;
    changeLinkText?: string;
    changeLinkTooltip?: string;
    modalTitle?: string;
}

const props = withDefaults(defineProps<Props>(), {
    historyCaption: "Target history",
    changeLinkText: "change",
    changeLinkTooltip: "Change target history",
    modalTitle: "Select a history",
});

const emit = defineEmits<{
    (e: "select-history", history: { id: string }): void;
}>();

const showModal = ref(false);

const userStore = useUserStore();
const { isAnonymous } = storeToRefs(userStore);

const historyStore = useHistoryStore();
const { histories } = storeToRefs(historyStore);

const canChangeHistory = computed(() => {
    return !isAnonymous.value && Array.isArray(histories.value) && histories.value.length > 1;
});

const { warningMessage } = useTargetHistoryUploadState(computed(() => props.targetHistoryId));

function openHistorySelector() {
    console.debug("Opening history selector modal");
    showModal.value = true;
}

function handleHistorySelected(history: { id: string }) {
    showModal.value = false;
    emit("select-history", history);
}
</script>

<template>
    <div>
        <div class="d-flex align-items-center">
            <TargetHistoryLink :target-history-id="targetHistoryId" :target-history-caption="historyCaption" />
            <a
                v-if="canChangeHistory"
                v-b-tooltip.hover.noninteractive
                href="#"
                class="change-history-link ml-2"
                :title="changeLinkTooltip"
                @click.prevent="openHistorySelector">
                {{ changeLinkText }}
            </a>
        </div>

        <BAlert v-if="warningMessage" show variant="warning" class="mb-2 py-1">
            {{ warningMessage }}
        </BAlert>

        <SelectorModal
            v-if="canChangeHistory"
            :histories="histories"
            :show-modal.sync="showModal"
            :title="modalTitle"
            @selectHistory="handleHistorySelected" />
    </div>
</template>

<style scoped lang="scss">
@import "@/style/scss/theme/blue.scss";

.change-history-link {
    &:hover {
        text-decoration: underline;
        color: $brand-primary;
    }
}
</style>

<script setup lang="ts">
import { faChevronDown, faChevronRight } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";

import type { CardBadge } from "@/components/Common/GCard.types";
import { useHistoryStore } from "@/stores/historyStore";

import type { BatchWithProgressAndUploads } from "./uploadProgressUi";
import { getBatchDisplayInfo, getBatchProgressSummary, getBatchProgressUi } from "./uploadProgressUi";

import UploadFileRow from "./UploadFileRow.vue";
import UploadItemCard from "./UploadItemCard.vue";
import SwitchToHistoryLink from "@/components/History/SwitchToHistoryLink.vue";

interface Props {
    batch: BatchWithProgressAndUploads;
    expanded: boolean;
}

const props = defineProps<Props>();
const emit = defineEmits<{
    (e: "toggle"): void;
}>();

const historyStore = useHistoryStore();

const ui = computed(() => getBatchProgressUi(props.batch));
const displayInfo = computed(() => getBatchDisplayInfo(props.batch));
const progressSummary = computed(() => getBatchProgressSummary(props.batch));

const hasError = computed(() => props.batch.status === "error");

const targetHistoryId = computed<string | null>(() => props.batch.uploads?.[0]?.targetHistoryId ?? null);

const resolvedTargetHistoryId = computed<string | null>(() => {
    const id = targetHistoryId.value;
    if (!id || id === historyStore.currentHistoryId) {
        return null;
    }
    return id;
});

const badges = computed<CardBadge[]>(() => [
    {
        id: "collection-type",
        label: props.batch.type,
        title: `Collection type: ${props.batch.type}`,
        variant: "primary",
        type: "badge" as const,
    },
]);
</script>

<template>
    <div class="batch-wrapper mb-3">
        <UploadItemCard :has-error="hasError" :badges="badges" clickable @click="emit('toggle')">
            <template v-slot:title>
                <div class="batch-title d-flex align-items-start w-100">
                    <FontAwesomeIcon
                        :icon="ui.icon"
                        :class="ui.textClass"
                        :spin="ui.spin"
                        class="mr-2 mt-1"
                        fixed-width />
                    <div class="flex-grow-1 min-width-0">
                        <div class="batch-name text-truncate">{{ batch.name }}</div>
                        <div class="batch-subtitle text-muted small">
                            {{ ui.label }}
                        </div>
                    </div>
                </div>
            </template>

            <template v-slot:indicators>
                <span class="text-muted small mr-3">{{ displayInfo.uploadModeSummary }}</span>
                <span class="text-muted small mr-3">{{ progressSummary }}</span>
                <span v-if="resolvedTargetHistoryId" class="small mr-3">
                    <span class="text-muted mr-1">Target:</span>
                    <SwitchToHistoryLink :history-id="resolvedTargetHistoryId" inline thin />
                </span>
                <FontAwesomeIcon
                    :icon="expanded ? faChevronDown : faChevronRight"
                    class="expand-icon mr-2 text-muted"
                    fixed-width />
            </template>

            <template v-slot:description>
                <transition name="fade">
                    <div v-if="batch.error" class="batch-error mt-2 p-2">
                        <div class="d-flex flex-column">
                            <div class="text-danger mb-2">{{ batch.error }}</div>
                            <div class="text-muted small">
                                You can try to manually create the collection from your history.
                            </div>
                        </div>
                    </div>
                </transition>

                <div class="progress batch-progress mt-2" style="height: 3px">
                    <div
                        class="progress-bar"
                        :class="ui.barClass"
                        :style="{ width: `${batch.progress}%` }"
                        role="progressbar"
                        :aria-valuenow="batch.progress"
                        aria-valuemin="0"
                        aria-valuemax="100" />
                </div>

                <div v-if="expanded" class="batch-uploads mt-2 pl-3">
                    <UploadFileRow v-for="file in batch.uploads" :key="file.id || file.name" :file="file" nested />
                </div>
            </template>
        </UploadItemCard>
    </div>
</template>

<style scoped lang="scss">
@import "@/style/scss/theme/blue.scss";

.batch-name {
    font-weight: 600;
}

.batch-subtitle {
    line-height: 1.2;
}

.batch-uploads {
    border-left: 2px solid $border-color;
}

.batch-error {
    background-color: lighten($brand-danger, 45%);
    border: 1px solid lighten($brand-danger, 30%);
    border-radius: $border-radius-base;
}

.fade-enter-active,
.fade-leave-active {
    transition: opacity 0.15s ease;
}

.fade-enter-from,
.fade-leave-to {
    opacity: 0;
}
</style>

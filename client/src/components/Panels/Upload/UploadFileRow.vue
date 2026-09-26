<script setup lang="ts">
import {
    faArrowRight,
    faChevronDown,
    faChevronRight,
    faFile,
    faLink,
    faPaste,
    faTimesCircle,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, ref } from "vue";

import type { CompositeFileUploadItem, CompositeSlotQueueItem, UploadItem } from "@/composables/upload/uploadItemTypes";
import { isCancellableUpload } from "@/composables/upload/uploadItemTypes";
import { useHistoryStore } from "@/stores/historyStore";
import { bytesToString } from "@/utils/utils";

import { getFileProgressUi, getFileStatusMessage, getUploadItemDisplayInfo } from "./uploadProgressUi";

import UploadItemCard from "./UploadItemCard.vue";
import CopyToClipboard from "@/components/CopyToClipboard.vue";
import SwitchToHistoryLink from "@/components/History/SwitchToHistoryLink.vue";
import UtcDate from "@/components/UtcDate.vue";

interface Props {
    file: UploadItem;
    nested?: boolean;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "cancel", id: string): void;
    (e: "dismiss", id: string): void;
}>();

const historyStore = useHistoryStore();

const ui = computed(() => getFileProgressUi(props.file));
const displayInfo = computed(() => getUploadItemDisplayInfo(props.file));
const statusMessage = computed(() => getFileStatusMessage(props.file));
const uploadedAtIso = computed(() => new Date(props.file.createdAt).toISOString());

const targetHistoryName = computed(() =>
    props.file.targetHistoryId ? historyStore.getHistoryNameById(props.file.targetHistoryId) : undefined,
);

const isDifferentHistory = computed(
    () => props.file.targetHistoryId && props.file.targetHistoryId !== historyStore.currentHistoryId,
);

const hasError = computed(() => props.file.status === "error");

const sourceUrl = computed(() => displayInfo.value.sourceUrl);

const isCancellable = computed(() => !props.nested && isCancellableUpload(props.file));
const canDismiss = computed(() => !props.nested && props.file.status === "error");

const cardBadges = computed(() => {
    const badges = [] as any[];
    displayInfo.value.badges.forEach((badge) => badges.push(badge));
    return badges;
});

const compositeSlots = computed<CompositeSlotQueueItem[]>(() =>
    props.file.uploadMode === "composite-file" ? ((props.file as CompositeFileUploadItem).slots ?? []) : [],
);

/** True when at least one slot has no known size (plain URL slots). The total is therefore an estimate. */
const hasSizeUncertainty = computed(() => compositeSlots.value.some((s) => s.fileSize === undefined));

/** Size is unknown for URL uploads (size is 0) — hide it rather than showing "0 bytes". */
const showSize = computed(() => props.file.size > 0);

const sizeLabel = computed(() => {
    const label = bytesToString(props.file.size);
    return hasSizeUncertainty.value ? `~${label}` : label;
});

const sizeTooltip = computed(() =>
    hasSizeUncertainty.value ? "Approximate — URL slot sizes are resolved by the server after fetch" : undefined,
);

const slotsExpanded = ref(false);

function slotIcon(src: CompositeSlotQueueItem["src"]) {
    if (src === "files") {
        return faFile;
    }
    if (src === "url") {
        return faLink;
    }
    return faPaste;
}

function slotSizeLabel(fileSize: number | undefined) {
    return fileSize !== undefined ? bytesToString(fileSize) : "size unknown";
}

function onCardClick() {
    if (compositeSlots.value.length > 0) {
        slotsExpanded.value = !slotsExpanded.value;
    }
}

function onCancel(event: Event) {
    event.stopPropagation();
    emit("cancel", props.file.id);
}

function onDismiss(event: Event) {
    event.stopPropagation();
    emit("dismiss", props.file.id);
}
</script>

<template>
    <UploadItemCard :nested="nested" :has-error="hasError" :badges="cardBadges" clickable @click="onCardClick">
        <template v-slot:title>
            <FontAwesomeIcon :icon="ui.icon" :class="ui.textClass" :spin="ui.spin" class="mr-2" fixed-width size="sm" />
            <FontAwesomeIcon
                v-if="displayInfo.icon"
                :icon="displayInfo.icon"
                class="mr-2 text-muted"
                fixed-width
                size="sm"
                :title="displayInfo.iconTitle" />
            <span class="file-name" :title="props.file.name">{{ props.file.name }}</span>
            <span v-if="targetHistoryName" class="text-muted small ml-2 text-truncate" :title="targetHistoryName">
                <template v-if="isDifferentHistory">
                    — History:
                    <SwitchToHistoryLink :history-id="props.file.targetHistoryId" inline thin />
                </template>
                <template v-else> — History: {{ targetHistoryName }} (current)</template>
            </span>
        </template>

        <template v-slot:indicators>
            <span
                v-if="showSize"
                class="text-muted small mr-2"
                :class="{ 'font-italic': hasSizeUncertainty }"
                :title="sizeTooltip">
                {{ sizeLabel }}
            </span>
            <span class="text-muted small mr-2">
                <UtcDate :date="uploadedAtIso" mode="elapsed" />
            </span>
            <span class="text-muted small mr-2">{{ props.file.progress }}%</span>
            <span v-if="compositeSlots.length > 0" class="text-muted small mr-2">
                <FontAwesomeIcon :icon="slotsExpanded ? faChevronDown : faChevronRight" fixed-width size="xs" />
                <span class="ml-1"> {{ compositeSlots.length }} slot{{ compositeSlots.length !== 1 ? "s" : "" }} </span>
            </span>
            <button
                v-if="isCancellable"
                class="btn btn-link text-muted p-0 ml-1 cancel-btn"
                title="Cancel upload"
                @click="onCancel">
                <FontAwesomeIcon :icon="faTimesCircle" fixed-width />
            </button>
            <button
                v-if="canDismiss"
                class="btn btn-link text-muted p-0 ml-1 cancel-btn"
                title="Dismiss upload"
                @click="onDismiss">
                <FontAwesomeIcon :icon="faTimesCircle" fixed-width />
            </button>
        </template>

        <template v-slot:description>
            <div class="progress" style="height: 3px">
                <div
                    class="progress-bar"
                    :class="ui.barClass"
                    :style="{ width: `${props.file.progress}%` }"
                    role="progressbar"
                    :aria-valuenow="props.file.progress"
                    aria-valuemin="0"
                    aria-valuemax="100"></div>
            </div>
            <div v-if="statusMessage" class="status-message text-muted small mt-1">
                {{ statusMessage }}
            </div>
            <div v-if="sourceUrl" class="source-url text-muted small mt-1">
                <span class="source-url-text text-truncate" :title="sourceUrl">{{ sourceUrl }}</span>
                <CopyToClipboard
                    class="copy-url-icon ml-1"
                    :text="sourceUrl"
                    message="Link copied to clipboard"
                    title="Copy link" />
            </div>
            <div v-if="props.file.error" class="error-message text-danger small mt-1">
                {{ props.file.error }}
            </div>

            <div v-if="slotsExpanded" class="slot-list mt-2 pl-3">
                <div
                    v-for="slot in compositeSlots"
                    :key="slot.slotName"
                    class="slot-row d-flex align-items-baseline py-1">
                    <FontAwesomeIcon
                        :icon="slotIcon(slot.src)"
                        class="text-muted mr-2 flex-shrink-0"
                        fixed-width
                        size="xs" />
                    <span class="text-monospace small mr-2 flex-shrink-0">{{ slot.slotName }}</span>
                    <span v-if="slot.description" class="text-muted small mr-2 text-truncate" :title="slot.description">
                        {{ slot.description }}
                    </span>
                    <FontAwesomeIcon :icon="faArrowRight" class="text-muted mr-2 flex-shrink-0" fixed-width size="xs" />
                    <span
                        class="small mr-2 flex-grow-1 text-truncate text-muted"
                        :class="{ 'font-italic': !slot.displayName }"
                        :title="slot.displayName || undefined">
                        {{ slot.displayName || "Not provided" }}
                    </span>
                    <span
                        v-if="slot.fileSize !== 0"
                        class="small flex-shrink-0 text-muted"
                        :class="{ 'font-italic': slot.fileSize === undefined }">
                        {{ slotSizeLabel(slot.fileSize) }}
                    </span>
                </div>
            </div>
        </template>
    </UploadItemCard>
</template>

<style scoped lang="scss">
@import "@/style/scss/theme/blue.scss";
@import "./uploadButtons";

.slot-list {
    border-top: 1px solid $border-color;
    border-left: 2px solid $border-color;
    padding-top: 0.25rem;
}

.slot-row + .slot-row {
    border-top: 1px solid $border-color;
}

.source-url {
    display: flex;
    align-items: center;

    .source-url-text {
        flex: 1 1 auto;
        min-width: 0;
    }

    .copy-url-icon {
        flex-shrink: 0;
        visibility: hidden;
    }

    &:hover .copy-url-icon {
        visibility: visible;
    }
}

@include cancel-button;
</style>

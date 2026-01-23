<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";

import type { UploadItem } from "@/composables/upload/uploadItemTypes";
import { useHistoryStore } from "@/stores/historyStore";
import { bytesToString } from "@/utils/utils";

import { getFileProgressUi, getUploadItemDisplayInfo } from "./uploadProgressUi";

import UploadItemCard from "./UploadItemCard.vue";
import SwitchToHistoryLink from "@/components/History/SwitchToHistoryLink.vue";
import UtcDate from "@/components/UtcDate.vue";

interface Props {
    file: UploadItem;
    nested?: boolean;
}

const props = defineProps<Props>();

const historyStore = useHistoryStore();

const ui = computed(() => getFileProgressUi(props.file));
const displayInfo = computed(() => getUploadItemDisplayInfo(props.file));
const uploadedAtIso = computed(() => new Date(props.file.createdAt).toISOString());

const targetHistoryName = computed(() =>
    props.file.targetHistoryId ? historyStore.getHistoryNameById(props.file.targetHistoryId) : undefined,
);

const isDifferentHistory = computed(
    () => props.file.targetHistoryId && props.file.targetHistoryId !== historyStore.currentHistoryId,
);

const hasError = computed(() => props.file.status === "error");

const cardBadges = computed(() => {
    const badges = [] as any[];

    displayInfo.value.badges.forEach((badge) => {
        badges.push(badge);
    });

    return badges;
});
</script>

<template>
    <UploadItemCard :nested="nested" :has-error="hasError" :badges="cardBadges" clickable>
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
            <span class="text-muted small mr-2">{{ bytesToString(props.file.size) }}</span>
            <span class="text-muted small mr-2">
                <UtcDate :date="uploadedAtIso" mode="elapsed" />
            </span>
            <span class="text-muted small mr-2">{{ props.file.progress }}%</span>
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
            <div v-if="props.file.error" class="error-message text-danger small mt-1">
                {{ props.file.error }}
            </div>
        </template>
    </UploadItemCard>
</template>

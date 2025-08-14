<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed } from "vue";
import { useRouter } from "vue-router/composables";

import { userOwnsHistory } from "@/api";
import type { AnyHistoryEntry } from "@/api/histories";
import { isArchivedHistory, isMyHistory } from "@/api/histories";
import { useHistoryCardActions } from "@/components/History/useHistoryCardActions";
import { useHistoryCardBadges } from "@/components/History/useHistoryCardBadges";
import { useHistoryCardIndicators } from "@/components/History/useHistoryCardIndicators";
import { useHistoryStore } from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";
import localize from "@/utils/localization";

import ExportRecordDOILink from "@/components/Common/ExportRecordDOILink.vue";
import GCard from "@/components/Common/GCard.vue";
import HistoryDatasetsBadge from "@/components/History/HistoryDatasetsBadge.vue";

interface Props {
    history: AnyHistoryEntry;
    archivedView: boolean;
    gridView: boolean;
    publishedView: boolean;
    selectable: boolean;
    selected: boolean;
    sharedView: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    archivedView: false,
    gridView: false,
    publishedView: false,
    selectable: false,
    selected: false,
    sharedView: false,
});

const router = useRouter();

const historyStore = useHistoryStore();

const userStore = useUserStore();
const { currentUser } = storeToRefs(userStore);

const emit = defineEmits<{
    (e: "select", history: AnyHistoryEntry): void;
    (e: "titleClick", history: AnyHistoryEntry["id"]): void;
    (e: "tagClick", tag: string): void;
    (e: "refreshList", overlayLoading?: boolean, silent?: boolean): void;
    (e: "updateFilter", key: string, value: any): void;
}>();

function onTitleClick() {
    router.push(`/histories/view?id=${props.history.id}`);
}

const historyCardTitle = computed(() => {
    return {
        label: props.history.name,
        title: localize("Click to view this history"),
        handler: onTitleClick,
    };
});

const { historyCardExtraActions, historyCardSecondaryActions, historyCardPrimaryActions } = useHistoryCardActions(
    computed(() => props.history),
    props.archivedView,
    () => emit("refreshList", true)
);

const { historyCardIndicators } = useHistoryCardIndicators(
    computed(() => props.history),
    props.archivedView,
    (k, v) => emit("updateFilter", k, v)
);

const { historyCardTitleBadges } = useHistoryCardBadges(
    computed(() => props.history),
    props.sharedView,
    props.publishedView,
    (k, v) => emit("updateFilter", k, v)
);

async function onTagsUpdate(historyId: string, tags: string[]) {
    await historyStore.updateHistory(historyId, { tags: tags });
    emit("refreshList", true, true);
}
</script>

<template>
    <GCard
        :id="`history-${history.id}`"
        :key="history.id"
        :title="historyCardTitle"
        :title-badges="historyCardTitleBadges"
        :title-n-lines="2"
        :can-rename-title="!history.deleted && !history.purged && isMyHistory(history)"
        :description="history.annotation || ''"
        :grid-view="props.gridView"
        :indicators="historyCardIndicators"
        :extra-actions="historyCardExtraActions"
        :primary-actions="historyCardPrimaryActions"
        :secondary-actions="historyCardSecondaryActions"
        :published="history.published"
        :selectable="props.selectable"
        :selected="props.selected"
        :tags="history.tags"
        :tags-editable="userOwnsHistory(currentUser, history)"
        :max-visible-tags="props.gridView ? 2 : 8"
        :update-time="history.update_time"
        @titleClick="onTitleClick"
        @rename="() => router.push(`/histories/rename?id=${history.id}`)"
        @select="isMyHistory(history) && emit('select', history)"
        @tagsUpdate="(tags) => onTagsUpdate(history.id, tags)"
        @tagClick="(tag) => emit('tagClick', tag)">
        <template v-if="props.archivedView && isArchivedHistory(history)" v-slot:titleActions>
            <ExportRecordDOILink :export-record-uri="history.export_record_data?.target_uri" />
        </template>

        <template v-slot:badges>
            <HistoryDatasetsBadge :history-id="history.id" :count="history.count" />
        </template>
    </GCard>
</template>

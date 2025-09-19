<script setup lang="ts">
import { computed } from "vue";
import { useRouter } from "vue-router/composables";

import { useDownloadTracker } from "@/composables/downloadTracker";
import type { MonitoringRequest } from "@/composables/persistentProgressMonitor";
import { useRoundRobinSelector } from "@/composables/roundRobinSelector";
import { DEFAULT_POLL_DELAY } from "@/composables/shortTermStorageMonitor";
import { useUserStore } from "@/stores/userStore";

import BreadcrumbHeading from "@/components/Common/BreadcrumbHeading.vue";
import ListHeader from "@/components/Common/ListHeader.vue";
import DownloadItemCard from "@/components/Downloads/DownloadItemCard.vue";

const router = useRouter();

const userStore = useUserStore();
const { downloadMonitoringData, untrackDownloadRequest } = useDownloadTracker();

const isEmpty = computed(() => {
    return downloadMonitoringData.value.length === 0;
});

const currentListView = computed(() => userStore.currentListViewPreferences.recentDownloads || "grid");

function onGoTo(to: string): void {
    router.push(to);
}

function onDelete(request: MonitoringRequest): void {
    untrackDownloadRequest(request);
}

function onDownload(url: string): void {
    window.open(url, "_blank");
}

const downloadsInProgress = computed(() => {
    return downloadMonitoringData.value.filter((data) => !data.isFinal);
});

const roundRobinSelector = useRoundRobinSelector(downloadsInProgress, DEFAULT_POLL_DELAY);

const taskIdToUpdate = computed(() => {
    return roundRobinSelector.currentItem.value?.taskId ?? null;
});

const breadcrumbItems = [{ title: "Recent Exports & Downloads", to: "/downloads" }];
</script>

<template>
    <div class="recent-downloads">
        <BreadcrumbHeading h1 separator inline :items="breadcrumbItems" />

        <ListHeader v-if="!isEmpty" list-id="recentDownloads" show-view-toggle />

        <p v-if="isEmpty">
            No recent exports or downloads found. When you start a long-running export or download, it will appear here.
        </p>
        <div v-else class="d-flex flex-wrap">
            <DownloadItemCard
                v-for="download in downloadMonitoringData"
                :key="download.taskId"
                :monitoring-data="download"
                :update-task-id="taskIdToUpdate"
                :grid-view="currentListView == 'grid'"
                @onGoTo="onGoTo"
                @onDelete="onDelete"
                @onDownload="onDownload" />
        </div>
    </div>
</template>

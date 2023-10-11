<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed } from "vue";

import { type BroadcastNotification, useBroadcastsStore } from "@/stores/broadcastsStore";

import BroadcastContainer from "@/components/Notifications/Broadcasts/BroadcastContainer.vue";

const { activeBroadcasts } = storeToRefs(useBroadcastsStore());

const currentBroadcast = computed(() => getNextActiveBroadcast());

function sortByPublicationTime(a: BroadcastNotification, b: BroadcastNotification) {
    return new Date(a.publication_time).getTime() - new Date(b.publication_time).getTime();
}

function getNextActiveBroadcast(): BroadcastNotification | undefined {
    return activeBroadcasts.value.sort(sortByPublicationTime).at(0);
}
</script>

<template>
    <div v-if="currentBroadcast">
        <BroadcastContainer :options="{ broadcast: currentBroadcast }" />
    </div>
</template>

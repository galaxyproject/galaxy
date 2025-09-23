<script setup lang="ts">
import { computed, watch } from "vue";

import { useJobStore } from "@/stores/jobStore";

import SwitchToHistoryLink from "@/components/History/SwitchToHistoryLink.vue";

interface Props {
    jobId: string;
    linkToList: string;
    identifierTextPlural: string;
    identifierTextCapitalized: string;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "dismissed"): void;
}>();

const jobStore = useJobStore();

const historyId = computed(() => {
    return jobStore.getJob(props.jobId)?.history_id;
});

async function init() {
    jobStore.fetchJob({ id: props.jobId });
}

watch(() => props.jobId, init, { immediate: true });
</script>

<template>
    <b-alert show variant="success" dismissible @dismissed="emit('dismissed')">
        <span class="mb-1 h-sm">Done!</span>
        <p v-if="historyId">
            {{ identifierTextCapitalized }} imported into
            <SwitchToHistoryLink v-if="historyId" :thin="false" :inline="true" :history-id="historyId" />
            (click the history name to switch to the history containing the import or check out
            <router-link :to="linkToList">your {{ identifierTextPlural }}</router-link
            >)
        </p>
        <p v-else>
            {{ identifierTextCapitalized }} imported, check out
            <router-link :to="linkToList">your {{ identifierTextPlural }}</router-link>
        </p>
    </b-alert>
</template>

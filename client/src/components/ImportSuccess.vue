<script setup lang="ts">
import { computed, toRef } from "vue";

import { useJobDetails } from "@/composables/jobDetails";

import GAlert from "@/components/BaseComponents/GAlert.vue";
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

const { job } = useJobDetails(toRef(props, "jobId"), { poll: false });
const historyId = computed(() => job.value?.history_id);
</script>

<template>
    <GAlert show variant="success" dismissible @dismissed="emit('dismissed')">
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
    </GAlert>
</template>

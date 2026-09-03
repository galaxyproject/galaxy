<script setup lang="ts">
import { faClock } from "@fortawesome/free-regular-svg-icons";
import { faHdd, faWrench } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { storeToRefs } from "pinia";
import { useRouter } from "vue-router/composables";

import type { JobBaseModel } from "@/api/jobs";
import { useHistoryStore } from "@/stores/historyStore";

import GCard from "@/components/Common/GCard.vue";
import Heading from "@/components/Common/Heading.vue";
import JobState from "@/components/JobStates/JobState.vue";

const props = defineProps<{
    job: JobBaseModel;
    current?: boolean;
}>();

const router = useRouter();

const { getHistoryNameById } = storeToRefs(useHistoryStore());

function cardClicked(job: JobBaseModel) {
    router.push(`/jobs/${job.id}/view`);
}
</script>

<template>
    <GCard
        :id="`job-${props.job.id}`"
        clickable
        button
        :current="props.current"
        :active="props.current"
        :title="props.job.tool_id"
        :title-icon="{ icon: faWrench }"
        :title-n-lines="2"
        title-size="text"
        :update-time="props.job.update_time"
        :update-time-icon="faClock"
        @click="() => cardClicked(props.job)">
        <template v-slot:description>
            <Heading v-if="props.job.history_id" class="m-0" size="text">
                <FontAwesomeIcon :icon="faHdd" fixed-width />

                <small class="text-muted truncate-n-lines two-lines">
                    {{ getHistoryNameById(props.job.history_id) }}
                </small>
            </Heading>
        </template>
        <template v-slot:badges>
            <JobState :job="props.job" />
        </template>
    </GCard>
</template>

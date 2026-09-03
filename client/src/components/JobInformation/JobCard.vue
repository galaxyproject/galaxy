<script setup lang="ts">
import { faClock } from "@fortawesome/free-regular-svg-icons";
import { faHdd, faRedo, faWrench } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { storeToRefs } from "pinia";
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";

import type { JobBaseModel } from "@/api/jobs";
import { useRerunnableTool } from "@/composables/rerunnableTool";
import { useHistoryStore } from "@/stores/historyStore";

import GCard from "@/components/Common/GCard.vue";
import Heading from "@/components/Common/Heading.vue";
import JobState from "@/components/JobStates/JobState.vue";

const props = defineProps<{
    job: JobBaseModel;
    current?: boolean;
}>();

const route = useRoute();
const router = useRouter();

const { getHistoryNameById } = storeToRefs(useHistoryStore());

const { canRerun: jobIsRerunnable } = useRerunnableTool(computed(() => props.job?.tool_id));

const actions = computed(() => {
    const actions = [];
    if (jobIsRerunnable.value) {
        actions.push({
            id: "rerun-job-action",
            icon: faRedo,
            label: "Rerun",
            title: "Rerun this job",
            to: `/?job_id=${props.job.id}`,
            disabled: route.fullPath === `/?job_id=${props.job.id}`,
        });
    }
    return actions;
});

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
        :title="props.job.tool_id"
        :title-icon="{ icon: faWrench }"
        :title-n-lines="2"
        title-size="text"
        :secondary-actions="actions"
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
            <JobState :job-id="props.job.id" :job="props.job" />
        </template>
    </GCard>
</template>

<style scoped lang="scss">
.truncate-n-lines {
    display: -webkit-box;
    -webkit-box-orient: vertical;
    overflow: hidden;
    word-break: break-word;
    overflow-wrap: break-word;
    &.two-lines {
        -webkit-line-clamp: 2;
        line-clamp: 2;
    }
}
</style>

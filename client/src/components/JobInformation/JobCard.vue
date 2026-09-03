<script setup lang="ts">
import { faClock } from "@fortawesome/free-regular-svg-icons";
import { faHdd, faRedo, faWrench } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { storeToRefs } from "pinia";
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router/composables";

import type { JobBaseModel } from "@/api/jobs";
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

/** Whether the job can be rerun; actually decided based on if the tool `is_workflow_compatible`,
 * but that would require an extra fetch. Just going by known non-rerunnable tool ids for now.
 */
const jobIsRerunnable = computed(
    () => !!props.job?.tool_id && !props.job.tool_id.startsWith("upload") && props.job.tool_id !== "__DATA_FETCH__",
);

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
            <JobState :job="props.job" />
        </template>
    </GCard>
</template>

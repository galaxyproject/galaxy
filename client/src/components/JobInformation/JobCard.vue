<script setup lang="ts">
import { faClock } from "@fortawesome/free-regular-svg-icons";
import { faHdd, faRedo, faWrench } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { storeToRefs } from "pinia";
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";

import type { JobBaseModel } from "@/api/jobs";
import type { CardAction } from "@/components/Common/GCard.types";
import { useRerunnableTool } from "@/composables/rerunnableTool";
import { useHistoryStore } from "@/stores/historyStore";
import { useToolStore } from "@/stores/toolStore";
import { getShortToolId } from "@/utils/tool";

import GCard from "@/components/Common/GCard.vue";
import Heading from "@/components/Common/Heading.vue";
import JobState from "@/components/JobStates/JobState.vue";

const props = defineProps<{
    job: JobBaseModel;
    current?: boolean;
    showToolName?: boolean;
}>();

const route = useRoute();
const router = useRouter();

const { getHistoryNameById } = storeToRefs(useHistoryStore());
const toolStore = useToolStore();

const { canRerun: jobIsRerunnable } = useRerunnableTool(computed(() => props.job?.tool_id));

const actions = computed(() => {
    const actions: CardAction[] = [];
    if (jobIsRerunnable.value) {
        actions.push({
            id: "rerun-job-action",
            icon: faRedo,
            label: "Rerun",
            title: "Rerun this job",
            to: `/?job_id=${props.job.id}`,
            variant: route.fullPath === `/?job_id=${props.job.id}` ? "primary" : undefined,
        });
    }
    return actions;
});

const cardTitle = computed(() => {
    const shortId = getShortToolId(props.job.tool_id);
    if (props.showToolName) {
        return toolStore.getToolNameById(props.job.tool_id, shortId);
    }
    return shortId;
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
        :secondary-actions="actions"
        :update-time="props.job.update_time"
        :update-time-icon="faClock"
        @click="() => cardClicked(props.job)">
        <template v-slot:title>
            <div class="d-flex align-items-start justify-content-between flex-gapx-1">
                <Heading class="job-card-title m-0" bold size="text">
                    <FontAwesomeIcon class="mr-1" :icon="faWrench" fixed-width />
                    <span v-g-tooltip.onoverflow class="job-card-title-text" :title="cardTitle">{{ cardTitle }}</span>
                </Heading>
                <JobState class="flex-shrink-0" :job-id="props.job.id" :job="props.job" />
            </div>
        </template>
        <template v-slot:description>
            <Heading v-if="props.job.history_id" class="m-0" size="text">
                <FontAwesomeIcon :icon="faHdd" fixed-width />

                <small class="text-muted truncate-n-lines two-lines">
                    {{ getHistoryNameById(props.job.history_id) }}
                </small>
            </Heading>
        </template>
    </GCard>
</template>

<style scoped lang="scss">
.job-card-title {
    display: flex;
    align-items: baseline;
    min-width: 0;

    .job-card-title-text {
        display: -webkit-box;
        -webkit-box-orient: vertical;
        -webkit-line-clamp: 2;
        line-clamp: 2;
        overflow: hidden;
        line-height: 1.2;
    }
}

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

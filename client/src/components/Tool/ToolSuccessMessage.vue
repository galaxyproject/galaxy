<script setup lang="ts">
import { computed } from "vue";
import { RouterLink } from "vue-router";

import type { JobResponse } from "@/api/jobs";

import ExternalLink from "../ExternalLink.vue";

const props = defineProps<{
    jobResponse: JobResponse;
    toolName: string;
}>();

const outputs = computed(() => props.jobResponse.outputs.concat(props.jobResponse.output_collections));

const nJobs = computed(() => (props.jobResponse && props.jobResponse.jobs ? props.jobResponse.jobs.length : 0));

const nJobsText = computed(() => (nJobs.value > 1 ? `${nJobs.value} jobs` : `1 job`));

const nOutputsText = computed(() => (outputs.value.length > 1 ? `${outputs.value.length} outputs` : `this output`));
</script>

<template>
    <div class="donemessagelarge">
        <p>
            Started tool <b>{{ props.toolName }}</b> and successfully added {{ nJobsText }} to the queue.
        </p>
        <p>It produces {{ nOutputsText }}:</p>
        <ul>
            <li v-for="item of outputs" :key="item.hid">
                <b>{{ item.hid }}: {{ item.name }}</b>
            </li>
        </ul>
        <p>
            You can check the status of queued jobs and view the resulting data by refreshing the History panel. When
            the job has been run the status will change from 'running' to 'finished' if completed successfully or
            'error' if problems were encountered.
        </p>
        <p v-if="nJobs > 1">
            Here is a link to each job:
            <ExternalLink v-for="job in jobResponse.jobs" :key="job.id" :href="`/jobs/${job.id}/view`">
                {{ job.id }}
            </ExternalLink>
        </p>
        <p v-else-if="jobResponse.jobs[0]">
            Here is a link to the job:
            <RouterLink :to="`/jobs/${jobResponse.jobs[0].id}/view`">
                {{ jobResponse.jobs[0]?.id }}
            </RouterLink>
        </p>
    </div>
</template>

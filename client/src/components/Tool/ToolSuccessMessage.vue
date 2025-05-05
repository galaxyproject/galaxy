<script setup lang="ts">
import { computed } from "vue";

import type { JobResponse } from "@/api/jobs";

const props = defineProps<{
    jobResponse: JobResponse;
    toolName: string;
}>();

const nOutputs = computed(() =>
    props.jobResponse && props.jobResponse.outputs ? props.jobResponse.outputs.length : 0
);

const nJobs = computed(() => (props.jobResponse && props.jobResponse.jobs ? props.jobResponse.jobs.length : 0));

const nJobsText = computed(() => (nJobs.value > 1 ? `${nJobs.value} jobs` : `1 job`));

const nOutputsText = computed(() => (nOutputs.value > 1 ? `${nOutputs.value} outputs` : `this output`));
</script>

<template>
    <div class="donemessagelarge">
        <p>
            Started tool <b>{{ props.toolName }}</b> and successfully added {{ nJobsText }} to the queue.
        </p>
        <p>It produces {{ nOutputsText }}:</p>
        <ul>
            <li v-for="item of props.jobResponse.outputs" :key="item.hid">
                <b>{{ item.hid }}: {{ item.name }}</b>
            </li>
        </ul>
        <p>
            You can check the status of queued jobs and view the resulting data by refreshing the History panel. When
            the job has been run the status will change from 'running' to 'finished' if completed successfully or
            'error' if problems were encountered.
        </p>
    </div>
</template>

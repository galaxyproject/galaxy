<script setup lang="ts">
import { computed } from "vue";

import type { JobBaseModel } from "@/api/jobs";

import Heading from "../Common/Heading.vue";
import CodeRow from "./CodeRow.vue";
import JobInformation from "./JobInformation.vue";
import JobHeader from "@/components/JobInformation/JobHeader.vue";
import JobMetrics from "@/components/JobMetrics/JobMetrics.vue";
import JobParameters from "@/components/JobParameters/JobParameters.vue";

const props = defineProps<{
    job?: JobBaseModel;
    jobId?: string;
    invocationId?: string;
    showHeader?: boolean;
}>();

const id = computed(() => props.job?.id || props.jobId);

// `traceback`, `info` and `remote_host` aren't on `JobBaseModel`: they're only present on the
// `admin_job_list` job objects passed in by the admin jobs table. `JobInformation` can't show the
// traceback itself since the `/api/jobs/{job_id}` response model doesn't include it.
const traceback = computed(() => (props.job && "traceback" in props.job ? (props.job.traceback as string) : null));
const info = computed(() => (props.job && "info" in props.job ? (props.job?.info as string) : null));
const remoteHost = computed(() => (props.job && "remote_host" in props.job ? (props.job.remote_host as string) : null));
</script>

<template>
    <div v-if="id">
        <JobHeader v-if="props.showHeader" :job-id="id" />
        <JobInformation :job-id="id" include-times :invocation-id="invocationId">
            <template v-slot:extra-code-rows>
                <!-- only needed for admin job component -->
                <CodeRow v-if="traceback" :code-label="'Traceback'" :code-item="traceback" />
                <CodeRow v-if="info" :code-label="'Info'" :code-item="info" />
                <CodeRow v-if="remoteHost" :code-label="'Remote Host'" :code-item="remoteHost" />
            </template>
        </JobInformation>
        <br />
        <Heading id="job-parameters-heading" h1 separator inline size="md"> Job Parameters </Heading>
        <JobParameters :job-id="id" :include-title="false" />
        <br />
        <Heading id="job-metrics-heading" h1 separator inline size="md"> Job Metrics </Heading>
        <JobMetrics :job-id="id" :include-title="false" />
    </div>
</template>

<style scoped>
.break-word {
    white-space: pre-wrap;
    word-break: break-word;
}
</style>

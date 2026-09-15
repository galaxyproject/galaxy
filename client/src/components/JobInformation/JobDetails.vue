<script setup lang="ts">
import { computed } from "vue";

import type { JobBaseModel } from "@/api/jobs";

import Heading from "../Common/Heading.vue";
import CodeRow from "./CodeRow.vue";
import JobInformation from "./JobInformation.vue";
import JobMetrics from "@/components/JobMetrics/JobMetrics.vue";
import JobParameters from "@/components/JobParameters/JobParameters.vue";

const props = defineProps<{
    job?: JobBaseModel;
    jobId?: string;
    invocationId?: string;
    showHeader?: boolean;
}>();

const id = computed(() => props.job?.id || props.jobId);

// Curious as to why we're trying to access info and remote_host like this, when they don't exist on
// `JobBaseModel`? Maybe in the admin view we fetch more properties? (leaving as is for now)
const info = computed(() => (props.job && "info" in props.job ? (props.job?.info as string) : null));
const remoteHost = computed(() => (props.job && "remote_host" in props.job ? (props.job.remote_host as string) : null));
</script>

<template>
    <div v-if="id">
        <JobInformation :job-id="id" include-times :include-title="showHeader" :invocation-id="invocationId">
            <template v-slot:extra-code-rows>
                <!-- only needed for admin job component -->
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

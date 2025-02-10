<script setup lang="ts">
import { computed } from "vue";

import { type ShowFullJobResponse } from "@/api/jobs";

interface Props {
    jobStderr?: string;
    toolStderr?: string;
    jobMessages?: ShowFullJobResponse["job_messages"];
}

const props = defineProps<Props>();

const hasMessages = computed(() => {
    return props.jobMessages && props.jobMessages.length > 0;
});
const hasDetails = computed(() => {
    return props.toolStderr || props.jobStderr || hasMessages.value;
});
</script>

<template>
    <div v-if="hasDetails">
        <h4 class="h-md">Details</h4>

        <div v-if="hasMessages" id="dataset-error-job-messages">
            <p>Execution resulted in the following messages:</p>

            <div v-for="(jobMessage, index) in jobMessages" :key="index">
                <pre class="rounded code">
                    {{ jobMessage["desc"] }}
                </pre>
            </div>
        </div>

        <div v-if="toolStderr">
            <p>Tool generated the following standard error:</p>
            
            <pre id="dataset-error-tool-stderr" class="rounded code">
                {{ toolStderr }}
            </pre>
        </div>

        <div v-if="jobStderr">
            <p>Galaxy job runner generated the following standard error:</p>

            <pre id="dataset-error-job-stderr" class="rounded code">
                {{ jobStderr }}
            </pre>
        </div>
    </div>
</template>

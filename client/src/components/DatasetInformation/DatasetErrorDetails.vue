<template>
    <div v-if="hasDetails">
        <h3>Details</h3>
        <div v-if="hasMessages" id="dataset-error-job-messages">
            <p>Execution resulted in the following messages:</p>
            <div v-for="(jobMessage, index) in jobMessages" :key="index">
                <pre class="rounded code">{{ jobMessage["desc"] }}</pre>
            </div>
        </div>
        <div v-if="toolStderr">
            <p>Tool generated the following standard error:</p>
            <pre id="dataset-error-tool-stderr" class="rounded code">{{ toolStderr }}</pre>
        </div>
        <div v-if="jobStderr">
            <p>Galaxy job runner generated the following standard error:</p>
            <pre id="dataset-error-job-stderr" class="rounded code">{{ jobStderr }}</pre>
        </div>
    </div>
</template>

<script>
export default {
    props: {
        toolStderr: {
            type: String,
            default: null,
        },
        jobStderr: {
            type: String,
            default: null,
        },
        jobMessages: {
            type: Array,
            default: null,
        },
    },
    computed: {
        hasDetails() {
            return this.toolStderr || this.jobStderr || this.hasMessages;
        },
        hasMessages() {
            return this.jobMessages && this.jobMessages.length > 0;
        },
    },
};
</script>

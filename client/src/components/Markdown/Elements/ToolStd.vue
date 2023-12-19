<script setup lang="ts">
import { computed } from "vue";

interface Job {
    tool_stdout?: string;
    tool_stderr?: string;
}

type JobsMap = {
    [key: string]: Job;
};

interface ToolStdProps {
    jobId: string;
    name: "tool_stderr" | "tool_stdout";
    jobs: JobsMap;
}

const props = defineProps<ToolStdProps>();

const jobContent = computed(() => {
    const job = props.jobs[props.jobId];
    return job && job[props.name];
});
</script>

<template>
    <b-card nobody class="content-height">
        <div :class="name" :job_id="jobId">
            <pre><code class="word-wrap-normal">{{ jobContent }}</code></pre>
        </div>
    </b-card>
</template>

<style scoped>
.content-height {
    max-height: 15rem;
    overflow-y: auto;
}
</style>

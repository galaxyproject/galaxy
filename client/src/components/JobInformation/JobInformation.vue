<script setup lang="ts">
import { computed, ref, watch } from "vue";

import { GalaxyApi } from "@/api";
import { type JobConsoleOutput, NON_TERMINAL_STATES, type ShowFullJobResponse } from "@/api/jobs";
import { JobConsoleOutputProvider, JobDetailsProvider } from "@/components/providers/JobProvider";
import { rethrowSimple } from "@/utils/simple-error";

import type { JobMessage } from "../../api/jobs";
import { getJobDuration } from "./utilities";

import Heading from "../Common/Heading.vue";
import DecodedId from "../DecodedId.vue";
import CodeRow from "./CodeRow.vue";
import CopyToClipboard from "@/components/CopyToClipboard.vue";
import HelpText from "@/components/Help/HelpText.vue";
import UtcDate from "@/components/UtcDate.vue";

const props = defineProps<{
    jobId: string;
    /** If `true`, the job's update and create times, as well as time to finish are shown. */
    includeTimes?: boolean;
    /** If provided, this component will skip fetching the invocation ID for the job. */
    invocationId?: string;
}>();

const job = ref<ShowFullJobResponse | null>(null);
const fetchedInvocationId = ref<string | null | undefined>(props.invocationId);

const stdout_length = ref(50000);
const stdout_text = ref("");
const stderr_length = ref(50000);
const stderr_text = ref("");

const stdout_position = computed(() => stdout_text.value.length);
const stderr_position = computed(() => stderr_text.value.length);

function jobStateIsTerminal(jobState: string) {
    return jobState && !NON_TERMINAL_STATES.includes(jobState);
}

function jobStateIsRunning(jobState: string) {
    return jobState == "running";
}

const jobIsTerminal = computed(() => (job.value?.state ? jobStateIsTerminal(job.value?.state) : false));
const jobIsRunning = computed(() => (job.value?.state ? jobStateIsRunning(job.value.state) : false));
const routeToInvocation = computed(() => `/workflows/invocations/${fetchedInvocationId.value}`);

// Curious as to why we're trying to access tool_version and traceback like this, when they don't exist on
// `ShowFullJobResponse`? Possibly historical reasons or maybe the `JobProvider` can return different types (doesn't seem like it)?
const toolVersion = computed(() =>
    job.value && "tool_version" in job.value ? (job.value?.tool_version as string) : null,
);
const traceback = computed(() => (job.value && "traceback" in job.value ? (job.value?.traceback as string) : null));

const metadataDetail = ref<Record<string, string>>({
    exit_code: `Tools may use exit codes to indicate specific execution errors. Many programs use 0 to indicate success and non-zero exit codes to indicate errors. Galaxy allows each tool to specify exit codes that indicate errors. https://docs.galaxyproject.org/en/master/dev/schema.html#tool-stdio-exit-code`,
    error_level: `NO_ERROR = 0</br>LOG = 1</br>QC = 1.1</br>WARNING = 2</br>FATAL = 3</br>FATAL_OOM = 4</br>MAX = 4`,
});

function updateJob(newJob: ShowFullJobResponse) {
    job.value = newJob;
    if (jobStateIsTerminal(newJob?.state)) {
        if (newJob.tool_stdout) {
            stdout_text.value = newJob.tool_stdout;
        }
        if (newJob.tool_stderr) {
            stderr_text.value = newJob.tool_stderr;
        }
    }
}

function updateConsoleOutputs(output: JobConsoleOutput) {
    // Keep stdout in memory and only fetch new text via JobProvider
    if (output) {
        if (output.stdout != null) {
            stdout_text.value += output.stdout;
        }
        if (output.stderr != null) {
            stderr_text.value += output.stderr;
        }
    }
}

function filterMetadata(jobMessages: JobMessage[]): Partial<JobMessage>[] {
    return jobMessages.map((item) => {
        return Object.entries(item).reduce((acc: Record<string, unknown>, [key, value]) => {
            if (value) {
                acc[key] = value;
            }
            return acc;
        }, {});
    });
}

async function fetchInvocationForJob(jobId: string) {
    const { data: invocations, error } = await GalaxyApi().GET("/api/invocations", {
        params: {
            query: { job_id: jobId },
        },
    });

    if (error) {
        rethrowSimple(error);
    }

    if (invocations.length) {
        return invocations[0];
    }

    return null;
}

// Fetches the invocation for the given job id to get the associated invocation id
watch(
    () => props.jobId,
    async (newId, oldId) => {
        if (
            newId &&
            (fetchedInvocationId.value === undefined || (fetchedInvocationId.value === null && newId !== oldId))
        ) {
            const invocation = await fetchInvocationForJob(newId);
            if (invocation) {
                fetchedInvocationId.value = invocation.id;
            } else {
                fetchedInvocationId.value = null;
            }
        }
    },
    { immediate: true },
);
</script>

<template>
    <div>
        <JobDetailsProvider auto-refresh :job-id="props.jobId" @update:result="updateJob" />
        <JobConsoleOutputProvider
            v-if="jobIsRunning"
            auto-refresh
            :job-id="props.jobId"
            :stdout_position="stdout_position"
            :stdout_length="stdout_length"
            :stderr_position="stderr_position"
            :stderr_length="stderr_length"
            @update:result="updateConsoleOutputs" />
        <Heading id="job-information-heading" h1 separator inline size="md"> Job Information </Heading>
        <table id="job-information" class="tabletip info_data_table">
            <tbody>
                <tr v-if="job && job.tool_id">
                    <td>Galaxy Tool ID</td>
                    <td id="galaxy-tool-id">
                        {{ job.tool_id }}
                        <CopyToClipboard
                            message="Tool ID was copied to your clipboard"
                            :text="job.tool_id"
                            title="Copy Tool ID" />
                    </td>
                </tr>
                <tr v-if="job && job.state">
                    <td>Job State</td>
                    <td data-description="galaxy-job-state">
                        <HelpText :uri="`galaxy.jobs.states.${job.state}`" :text="job.state" />
                    </td>
                </tr>
                <tr v-if="toolVersion">
                    <td>Galaxy Tool Version</td>
                    <td id="galaxy-tool-version">{{ toolVersion }}</td>
                </tr>
                <tr v-if="job && props.includeTimes">
                    <td>Created</td>
                    <td v-if="job.create_time" id="created">
                        <UtcDate :date="job.create_time" mode="pretty" />
                    </td>
                </tr>
                <tr v-if="job && props.includeTimes">
                    <td>Updated</td>
                    <td v-if="job.update_time" id="updated">
                        <UtcDate :date="job.update_time" mode="pretty" />
                    </td>
                </tr>
                <tr v-if="job && props.includeTimes && jobIsTerminal">
                    <td>Time To Finish</td>
                    <td id="runtime">
                        {{ getJobDuration(job) }}
                    </td>
                </tr>
                <CodeRow
                    v-if="job && job.command_line"
                    id="command-line"
                    help-uri="unix.commandLine"
                    :code-label="'Command Line'"
                    :code-item="job.command_line" />
                <CodeRow
                    v-if="job"
                    id="stdout"
                    help-uri="unix.stdout"
                    :code-label="'Tool Standard Output'"
                    :code-item="stdout_text" />
                <CodeRow
                    v-if="job"
                    id="stderr"
                    help-uri="unix.stderr"
                    :code-label="'Tool Standard Error'"
                    :code-item="stderr_text" />
                <CodeRow
                    v-if="traceback"
                    id="traceback"
                    help-uri="unix.traceback"
                    :code-label="'Unexpected Job Errors'"
                    :code-item="traceback" />
                <tr v-if="job">
                    <td>Tool <HelpText uri="unix.exitCode" text="Exit Code" /></td>
                    <td id="exit-code">{{ job.exit_code }}</td>
                </tr>
                <tr v-if="job && job.job_messages && job.job_messages.length > 0" id="job-messages">
                    <td>Job Messages</td>
                    <td>
                        <ul v-if="Array.isArray(job.job_messages)" class="pl-2 mb-0">
                            <div v-for="(message, m) in filterMetadata(job.job_messages)" :key="m" class="job-message">
                                <div v-if="job.job_messages.length > 1">
                                    <u>Job Message {{ m + 1 }}:</u>
                                </div>
                                <li v-for="(value, name, i) in message" :key="i">
                                    <span
                                        v-if="metadataDetail[name]"
                                        v-b-tooltip.html
                                        class="tooltipJobInfo"
                                        :title="metadataDetail[name]">
                                        <strong>{{ name }}:</strong>
                                    </span>
                                    <strong v-else>{{ name }}:</strong>
                                    {{ value }}
                                </li>
                                <hr v-if="m + 1 < job.job_messages.length" />
                            </div>
                        </ul>
                        <div v-else>
                            {{ job.job_messages }}
                        </div>
                    </td>
                </tr>
                <slot></slot>
                <tr v-if="job && job.id">
                    <td>Job API ID</td>
                    <td id="encoded-job-id">{{ job.id }} <DecodedId :id="job.id" /></td>
                </tr>
                <tr v-if="job && job.copied_from_job_id">
                    <td>Copied from Job API ID</td>
                    <td id="encoded-copied-from-job-id">
                        {{ job.copied_from_job_id }} <DecodedId :id="job.copied_from_job_id" />
                    </td>
                </tr>
                <tr v-if="fetchedInvocationId">
                    <td>Workflow Invocation</td>
                    <td>
                        <router-link :to="routeToInvocation">{{ fetchedInvocationId }}</router-link>
                    </td>
                </tr>
            </tbody>
        </table>
    </div>
</template>
<style scoped>
.tooltipJobInfo {
    text-decoration-line: underline;
    text-decoration-style: dashed;
}
</style>

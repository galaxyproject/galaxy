<script setup>
import CopyToClipboard from "components/CopyToClipboard";
import HelpText from "components/Help/HelpText";
import { JobDetailsProvider } from "components/providers/JobProvider";
import UtcDate from "components/UtcDate";
import { formatDuration, intervalToDuration } from "date-fns";
import JOB_STATES_MODEL from "utils/job-states-model";
import { computed, ref, watch } from "vue";

import { invocationForJob } from "@/api/invocations";

import DecodedId from "../DecodedId.vue";
import CodeRow from "./CodeRow.vue";

const job = ref(null);
const invocationId = ref(undefined);

const props = defineProps({
    job_id: {
        type: String,
        required: true,
    },
    includeTimes: {
        type: Boolean,
        default: false,
    },
});

const runTime = computed(() =>
    formatDuration(intervalToDuration({ start: new Date(job.value.create_time), end: new Date(job.value.update_time) }))
);

const jobIsTerminal = computed(() => job.value && !JOB_STATES_MODEL.NON_TERMINAL_STATES.includes(job.value.state));

const routeToInvocation = computed(() => `/workflows/invocations/${invocationId.value}`);

const metadataDetail = ref({
    exit_code: `Tools may use exit codes to indicate specific execution errors. Many programs use 0 to indicate success and non-zero exit codes to indicate errors. Galaxy allows each tool to specify exit codes that indicate errors. https://docs.galaxyproject.org/en/master/dev/schema.html#tool-stdio-exit-code`,
    error_level: `NO_ERROR = 0</br>LOG = 1</br>QC = 1.1</br>WARNING = 2</br>FATAL = 3</br>FATAL_OOM = 4</br>MAX = 4`,
});

function updateJob(newJob) {
    job.value = newJob;
}

function filterMetadata(jobMessages) {
    return jobMessages.map((item) => {
        return Object.entries(item).reduce((acc, [key, value]) => {
            if (value) {
                acc[key] = value;
            }
            return acc;
        }, {});
    });
}

// Fetches the invocation for the given job id to get the associated invocation id
watch(
    () => props.job_id,
    async (newId, oldId) => {
        if (newId && (invocationId.value === undefined || newId !== oldId)) {
            const invocation = await invocationForJob({ jobId: newId });
            if (invocation) {
                invocationId.value = invocation.id;
            } else {
                invocationId.value = null;
            }
        }
    },
    { immediate: true }
);
</script>

<template>
    <div>
        <JobDetailsProvider auto-refresh :job-id="props.job_id" @update:result="updateJob" />
        <h2 class="h-md">Job Information</h2>
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
                <tr v-if="job && job.tool_version">
                    <td>Galaxy Tool Version</td>
                    <td id="galaxy-tool-version">{{ job.tool_version }}</td>
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
                        {{ runTime }}
                    </td>
                </tr>
                <CodeRow
                    v-if="job"
                    id="command-line"
                    help-uri="unix.commandLine"
                    :code-label="'Command Line'"
                    :code-item="job.command_line" />
                <CodeRow
                    v-if="job"
                    id="stdout"
                    help-uri="unix.stdout"
                    :code-label="'Tool Standard Output'"
                    :code-item="job.tool_stdout" />
                <CodeRow
                    v-if="job"
                    id="stderr"
                    help-uri="unix.stderr"
                    :code-label="'Tool Standard Error'"
                    :code-item="job.tool_stderr" />
                <CodeRow
                    v-if="job && job.traceback"
                    id="traceback"
                    help-uri="unix.traceback"
                    :code-label="'Unexpected Job Errors'"
                    :code-item="job.traceback" />
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
                                        :title="metadataDetail[name]"
                                        ><strong>{{ name }}:</strong></span
                                    >
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
                <tr v-if="invocationId">
                    <td>Workflow Invocation</td>
                    <td>
                        <router-link :to="routeToInvocation">{{ invocationId }}</router-link>
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

<script setup lang="ts">
import { faArrowRight, faInfoCircle, faRedo } from "@fortawesome/free-solid-svg-icons";
import { computed, ref, toRef, watch } from "vue";
import { useRoute } from "vue-router/composables";

import { GalaxyApi } from "@/api";
import type { CardAction } from "@/components/Common/GCard.types";
import { useJobConsoleOutput, useJobDetails } from "@/composables/jobDetails";
import { rethrowSimple } from "@/utils/simple-error";
import { stateIsTerminal } from "@/utils/utils";

import type { JobMessage } from "../../api/jobs";

import DecodedId from "../DecodedId.vue";
import CodeRow from "./CodeRow.vue";
import DetailBlock from "@/components/Common/DetailBlock.vue";
import GCard from "@/components/Common/GCard.vue";
import CopyToClipboard from "@/components/CopyToClipboard.vue";
import HelpText from "@/components/Help/HelpText.vue";
import UtcDate from "@/components/UtcDate.vue";

const props = withDefaults(
    defineProps<{
        jobId: string;
        /** If `true`, the job's update and create times, as well as time to finish are shown. */
        includeTimes?: boolean;
        /** If `true`, the rerun indicator is shown. */
        includeRerunIndicator?: boolean;
        /** If `true`, we render a "View full details" button */
        includeViewFullDetailsButton?: boolean;
        /** If provided, this component will skip fetching the invocation ID for the job. */
        invocationId?: string;
        /** If `true`, the section is collapsible */
        collapsible?: boolean;
    }>(),
    { invocationId: undefined },
);

const route = useRoute();

/** Invocation ID for the run that the job might have come from. It is `null` if the job has no associated invocation,
 * or `undefined` if it has not been fetched yet.
 */
const fetchedInvocationId = ref<string | null | undefined>(props.invocationId);

const { job } = useJobDetails(toRef(props, "jobId"));

const jobIsRunning = computed(() => job.value?.state === "running");

// Console output is only polled while the job is actively running
const consoleOutputJobId = computed(() => (jobIsRunning.value ? props.jobId : undefined));
const { stdout: stdout_text, stderr: stderr_text } = useJobConsoleOutput(consoleOutputJobId);

const routeToInvocation = computed(() => `/workflows/invocations/${fetchedInvocationId.value}`);

// Curious as to why we're trying to access tool_version and traceback like this, when they don't exist on
// `ShowFullJobResponse`? Possibly historical reasons or maybe the `JobProvider` can return different types (doesn't seem like it)?
const toolVersion = computed(() =>
    job.value && "tool_version" in job.value ? (job.value?.tool_version as string) : null,
);
const traceback = computed(() => (job.value && "traceback" in job.value ? (job.value?.traceback as string) : null));

const primaryActions = computed<CardAction[]>(() => {
    const actions: CardAction[] = [];
    if (props.includeViewFullDetailsButton && route.path !== `/jobs/${props.jobId}/view`) {
        actions.push({
            id: "go-to-job-details",
            class: "text-decoration-none",
            label: "View full details",
            icon: faArrowRight,
            title: "View full job details",
            to: `/jobs/${props.jobId}/view`,
            size: "md",
            variant: "link",
        });
    }
    if (props.includeRerunIndicator) {
        actions.push({
            id: "job-info-card-rerun",
            class: "text-decoration-none",
            label: "Rerun",
            icon: faRedo,
            title: "Rerun this job",
            to: `/?job_id=${props.jobId}`,
            size: "md",
            variant: "link",
        });
    }
    return actions;
});

const metadataDetail = ref<Record<string, string>>({
    exit_code: `Tools may use exit codes to indicate specific execution errors. Many programs use 0 to indicate success and non-zero exit codes to indicate errors. Galaxy allows each tool to specify exit codes that indicate errors. https://docs.galaxyproject.org/en/master/dev/schema.html#tool-stdio-exit-code`,
    error_level: `NO_ERROR = 0</br>LOG = 1</br>QC = 1.1</br>WARNING = 2</br>FATAL = 3</br>FATAL_OOM = 4</br>MAX = 4`,
});

// Once the job reaches a terminal state, prefer its own tool_stdout/tool_stderr as the final,
// complete output
watch(job, (newJob) => {
    if (newJob && stateIsTerminal({ state: newJob.state })) {
        stdout_text.value = newJob.tool_stdout ?? "";
        stderr_text.value = newJob.tool_stderr ?? "";
    }
});

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
        // Reset the fetched invocation ID if the job ID has changed and no invocation ID is provided via props
        if (!props.invocationId && newId !== oldId) {
            fetchedInvocationId.value = undefined;
        }

        // Fetch the invocation for the new job ID if it hasn't been fetched yet
        if (newId && fetchedInvocationId.value === undefined) {
            const invocation = await fetchInvocationForJob(newId);
            if (invocation) {
                fetchedInvocationId.value = invocation.id;
            } else {
                // The job does not have an associated invocation
                fetchedInvocationId.value = null;
            }
        }
    },
    { immediate: true },
);
</script>

<template>
    <DetailBlock :header-icon="faInfoCircle" title="Job Execution Details" :collapsible="props.collapsible">
        <template v-slot:custom-content>
            <GCard :primary-actions="primaryActions">
                <template v-slot:description>
                    <table id="job-information" class="tabletip info_data_table job-info-table">
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
                            <tr v-if="job && job.job_messages && job.job_messages.length > 0" id="job-messages">
                                <td>Job Messages</td>
                                <td>
                                    <ul v-if="Array.isArray(job.job_messages)" class="pl-2 mb-0">
                                        <div
                                            v-for="(message, m) in filterMetadata(job.job_messages)"
                                            :key="m"
                                            class="job-message">
                                            <div v-if="job.job_messages.length > 1">
                                                <u>Job Message {{ m + 1 }}:</u>
                                            </div>
                                            <li v-for="(value, name, i) in message" :key="i">
                                                <span
                                                    v-if="metadataDetail[name]"
                                                    v-g-tooltip.html
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

                            <slot name="extra-table-rows" />

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

                    <div class="px-2 py-2">
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
                        <CodeRow
                            v-if="job"
                            id="exit-code"
                            help-uri="unix.exitCode"
                            :code-label="'Tool Exit Code'"
                            :code-item="String(job.exit_code)" />
                        <slot name="extra-code-rows" />
                    </div>
                </template>

                <template v-slot:update-time>
                    <i v-if="props.includeViewFullDetailsButton" class="mb-0">
                        View more information on the details page.
                    </i>
                </template>
            </GCard>
        </template>
    </DetailBlock>
</template>
<style scoped lang="scss">
.tooltipJobInfo {
    text-decoration-line: underline;
    text-decoration-style: dashed;
}

.job-info-table {
    :deep(tr) {
        td {
            padding: 0.25rem 0.5rem;
            vertical-align: top;
            border-bottom: none;
        }

        &:hover td {
            background-color: var(--color-blue-100);
        }

        td:first-child {
            font-size: 0.78rem;
            font-weight: 700;
            color: var(--color-grey-600);
        }

        td:last-child {
            color: var(--color-blue-700);
        }
    }
}
</style>

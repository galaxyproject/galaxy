<template>
    <div>
        <JobDetailsProvider auto-refresh :job-id="job_id" @update:result="updateJob" />
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
                <tr v-if="job && includeTimes">
                    <td>Created</td>
                    <td v-if="job.create_time" id="created">
                        <UtcDate :date="job.create_time" mode="pretty" />
                    </td>
                </tr>
                <tr v-if="job && includeTimes">
                    <td>Updated</td>
                    <td v-if="job.update_time" id="updated">
                        <UtcDate :date="job.update_time" mode="pretty" />
                    </td>
                </tr>
                <tr v-if="job && includeTimes && jobIsTerminal">
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
                            <li v-for="(message, index) in job.job_messages" :key="index">
                                [{{ index }}]
                                <ul>
                                    <li v-for="(value, name, index) in message" :key="index">
                                        <strong>{{ name }}</strong>
                                        : {{ value }}
                                    </li>
                                </ul>
                            </li>
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

<script>
import CopyToClipboard from "components/CopyToClipboard";
import HelpText from "components/Help/HelpText";
import { JobDetailsProvider } from "components/providers/JobProvider";
import UtcDate from "components/UtcDate";
import { formatDuration, intervalToDuration } from "date-fns";
import { getAppRoot } from "onload/loadConfig";
import JOB_STATES_MODEL from "utils/job-states-model";

import { invocationForJob } from "@/api/invocations";

import DecodedId from "../DecodedId.vue";
import CodeRow from "./CodeRow.vue";

export default {
    components: {
        CodeRow,
        DecodedId,
        JobDetailsProvider,
        HelpText,
        UtcDate,
        CopyToClipboard,
    },
    props: {
        job_id: {
            type: String,
            required: true,
        },
        includeTimes: {
            type: Boolean,
            default: false,
        },
    },
    data() {
        return {
            job: null,
            invocationId: null,
        };
    },
    computed: {
        runTime: function () {
            return formatDuration(
                intervalToDuration({ start: new Date(this.job.create_time), end: new Date(this.job.update_time) })
            );
        },
        jobIsTerminal() {
            return this.job && !JOB_STATES_MODEL.NON_TERMINAL_STATES.includes(this.job.state);
        },
        routeToInvocation() {
            return `/workflows/invocations/${this.invocationId}`;
        },
    },
    methods: {
        getAppRoot() {
            return getAppRoot();
        },
        updateJob(job) {
            this.job = job;
            if (job) {
                this.fetchInvocation(job.id);
            }
        },
        async fetchInvocation(jobId) {
            if (jobId) {
                const invocation = await invocationForJob({ jobId: jobId });
                if (invocation) {
                    this.invocationId = invocation.id;
                }
            }
        },
    },
};
</script>

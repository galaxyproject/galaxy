<template>
    <div>
        <JobDetailsProvider auto-refresh :job-id="job_id" @update:result="updateJob"/>
        <JobConsoleOutputProvider
            auto-refresh
            :job-id="job_id"
            :stdout_position="stdout_position"
            :stdout_length="stdout_length"
            :stderr_position="stderr_position"
            :stderr_length="stderr_length"
            @update:result="updateConsoleOutputs"/>
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
                    <td data-description="galaxy-job-state">{{ job.state }}</td>
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
                <CodeRow v-if="job" id="command-line" :code-label="'Command Line'" :code-item="job.command_line" />
                <CodeRow v-if="job" id="stdout" :code-label="'Tool Standard Output'" :code-item="stdout_text" />
                <CodeRow v-if="job" id="stderr" :code-label="'Tool Standard Error'" :code-item="stderr_text" />
                <CodeRow
                    v-if="job && job.traceback"
                    id="traceback"
                    :code-label="'Unexpected Job Errors'"
                    :code-item="job.traceback" />
                <tr v-if="job">
                    <td>Tool Exit Code</td>
                    <td id="exit-code">{{ job.exit_code }}</td>
                </tr>
                <tr v-if="job && job.job_messages && job.job_messages.length > 0" id="job-messages">
                    <td>Job Messages</td>
                    <td>
                        <ul style="padding-left: 15px; margin-bottom: 0px">
                            <li v-for="(message, index) in job.job_messages" :key="index">{{ message }}</li>
                        </ul>
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
            </tbody>
        </table>
    </div>
</template>

<script>
import CopyToClipboard from "components/CopyToClipboard";
import { JobDetailsProvider, JobConsoleOutputProvider } from "components/providers/JobProvider";
import UtcDate from "components/UtcDate";
import { formatDuration, intervalToDuration } from "date-fns";
import { getAppRoot } from "onload/loadConfig";
import JOB_STATES_MODEL from "utils/job-states-model";

import DecodedId from "../DecodedId.vue";
import CodeRow from "./CodeRow.vue";

export default {
    components: {
        CodeRow,
        DecodedId,
        JobDetailsProvider,
        JobConsoleOutputProvider,
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
            stdout_position: 0,
            stdout_length: 50000,
            stdout_text: "",
            stderr_position: 0,
            stderr_length: 50000,
            stderr_text: "",
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
    },
    methods: {
        getAppRoot() {
            return getAppRoot();
        },
        updateJob(job) {
            this.job = job;
            // Load stored stdout and stderr
            if (this.jobIsTerminal) {
                if (job.tool_stdout) {
                    this.stdout_text += job.tool_stdout;
                    this.stdout_position += job.tool_stdout.length;
                }
                if (job.tool_stderr) {
                    this.stderr_text += job.tool_stderr;
                    this.stderr_position += job.tool_stderr.length;
                }
            }
        },
        updateConsoleOutputs(output) {
            // Keep stdout in memory and only fetch new text via JobProvider
            if (output && !this.jobIsTerminal) {
                if (output.stdout != null) {
                    this.stdout_text += output.stdout;
                    this.stdout_position += output.stdout.length;
                }
                if (output.stderr != null) {
                    this.stderr_text += output.stderr;
                    this.stderr_position += output.stderr.length;
                }
            }
        },
    },
};
</script>

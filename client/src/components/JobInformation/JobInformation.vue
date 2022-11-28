<template>
    <div>
        <job-details-provider auto-refresh :job-id="job_id" @update:result="updateJob" />
        <h3>Job Information</h3>
        <table id="job-information" class="tabletip info_data_table">
            <tbody>
                <tr v-if="job && job.tool_id">
                    <td>Galaxy Tool ID:</td>
                    <td id="galaxy-tool-id">
                        {{ job.tool_id }}
                        <copy-to-clipboard
                            message="Tool ID was copied to your clipboard"
                            :text="job.tool_id"
                            title="Copy Tool ID" />
                    </td>
                </tr>
                <tr v-if="job && job.tool_version">
                    <td>Galaxy Tool Version:</td>
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
                <code-row v-if="job" id="command-line" :code-label="'Command Line'" :code-item="job.command_line" />
                <code-row v-if="job" id="stdout" :code-label="'Tool Standard Output'" :code-item="job.tool_stdout" />
                <code-row v-if="job" id="stderr" :code-label="'Tool Standard Error'" :code-item="job.tool_stderr" />
                <code-row
                    v-if="job && job.traceback"
                    id="traceback"
                    :code-label="'Unexpected Job Errors'"
                    :code-item="job.traceback" />
                <tr v-if="job">
                    <td>Tool Exit Code:</td>
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
                    <td>Job API ID:</td>
                    <td id="encoded-job-id">{{ job.id }} <decoded-id :id="job.id" /></td>
                </tr>
                <tr v-if="job && job.copied_from_job_id">
                    <td>Copied from Job API ID:</td>
                    <td id="encoded-copied-from-job-id">
                        {{ job.copied_from_job_id }} <decoded-id :id="job.copied_from_job_id" />
                    </td>
                </tr>
            </tbody>
        </table>
    </div>
</template>

<script>
import { getAppRoot } from "onload/loadConfig";
import DecodedId from "../DecodedId.vue";
import CodeRow from "./CodeRow.vue";
import { JobDetailsProvider } from "components/providers/JobProvider";
import UtcDate from "components/UtcDate";
import CopyToClipboard from "components/CopyToClipboard";
import JOB_STATES_MODEL from "mvc/history/job-states-model";
import { formatDuration, intervalToDuration } from "date-fns";

export default {
    components: {
        CodeRow,
        DecodedId,
        JobDetailsProvider,
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
        },
    },
};
</script>

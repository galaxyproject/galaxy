<template>
    <div>
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
                            title="Copy Tool ID"
                        />
                    </td>
                </tr>
                <tr v-if="job && job.tool_version">
                    <td>Galaxy Tool Version:</td>
                    <td id="galaxy-tool-version">{{ job.tool_version }}</td>
                </tr>
                <tr v-if="job && includeTimes">
                    <td>Created</td>
                    <td id="created" v-if="job.create_time">
                        <UtcDate :date="job.create_time" mode="pretty" />
                    </td>
                </tr>
                <tr v-if="job && includeTimes">
                    <td>Updated</td>
                    <td id="created" v-if="job.update_time">
                        <UtcDate :date="job.update_time" mode="pretty" />
                    </td>
                </tr>
                <code-row id="command-line" v-if="job" :codeLabel="'Command Line'" :codeItem="job.command_line" />
                <code-row id="stdout" v-if="job" :codeLabel="'Tool Standard Output'" :codeItem="job.tool_stdout" />
                <code-row id="stderr" v-if="job" :codeLabel="'Tool Standard Error'" :codeItem="job.tool_stderr" />
                <tr v-if="job">
                    <td>Tool Exit Code:</td>
                    <td id="exist-code">{{ job.exit_code }}</td>
                </tr>
                <tr id="job-messages" v-if="job && job.job_messages && job.job_messages.length > 0">
                    <td>Job Messages</td>
                    <td>
                        <ul style="padding-left: 15px; margin-bottom: 0px;">
                            <li v-for="message in job.job_messages" :key="message">{{ message }}</li>
                        </ul>
                    </td>
                </tr>
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
import { mapCacheActions } from "vuex-cache";
import { getAppRoot } from "onload/loadConfig";
import DecodedId from "../DecodedId.vue";
import CodeRow from "./CodeRow.vue";
import UtcDate from "components/UtcDate";
import CopyToClipboard from "components/CopyToClipboard";

export default {
    components: {
        CodeRow,
        DecodedId,
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
    created: function () {
        this.fetchJob(this.job_id);
    },
    computed: {
        job: function () {
            const job = this.$store.getters.job(this.job_id);
            return job;
        },
    },
    methods: {
        ...mapCacheActions(["fetchJob"]),
        getAppRoot() {
            return getAppRoot();
        },
    },
};
</script>

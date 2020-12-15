<template>
    <div>
        <h3>Job Information</h3>
        <table id="job-information" class="tabletip">
            <tbody>
                <tr v-if="job && job.tool_id">
                    <td>Galaxy Tool ID:</td>
                    <td id="galaxy-tool-id">{{ job.tool_id }}</td>
                </tr>
                <tr v-if="job && job.tool_version">
                    <td>Galaxy Tool Version:</td>
                    <td id="galaxy-tool-version">{{ job.tool_version }}</td>
                </tr>
                <tr v-if="dataset.tool_version">
                    <td>Tool Version:</td>
                    <td id="tool-version">{{ dataset.tool_version }}</td>
                </tr>
                <tr>
                    <td>Tool Standard Output:</td>
                    <td id="stdout"><a :href="`${getAppRoot()}datasets/${this.dataset.id}/stdout`">stdout</a></td>
                </tr>
                <tr>
                    <td>Tool Standard Error:</td>
                    <td id="stderr"><a :href="`${getAppRoot()}datasets/${this.dataset.id}/stderr`">stderr</a></td>
                </tr>

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

                <tr>
                    <td>History Content API ID:</td>
                    <td>
                        <div id="dataset-id">{{ dataset.id }}</div>
                        <div id="history-dataset-id" v-if="dataset.dataset_id">({{ dataset.dataset_id }})</div>
                    </td>
                </tr>

                <tr v-if="job">
                    <td>Job API ID:</td>
                    <td>
                        <div id="encoded-job-id">{{ job.id }}</div>
                        <div id="job-id" v-if="isEligibleForDecode && decoded_job_id">({{ decoded_job_id }})</div>
                    </td>
                </tr>
                <tr v-if="isCopiedFromJobId">
                    <td>Copied from Job API ID:</td>
                    <td>
                        <div id="encoded-copied-from-job-id">{{ job.copied_from_job_id }}</div>
                        <div id="copied-from-job-id" v-if="decoded_copied_from_job_id">
                            ({{ decoded_copied_from_job_id }})
                        </div>
                    </td>
                </tr>

                <tr v-if="dataset.history_id">
                    <td>History API ID:</td>
                    <td>
                        <div id="history_id">{{ dataset.history_id }}</div>
                        <div v-if="isEligibleForDecode && decoded_history_id">({{ decoded_history_id }})</div>
                    </td>
                </tr>

                <tr v-if="dataset.uuid">
                    <td>UUID:</td>
                    <td id="dataset-uuid">{{ dataset.uuid }}</td>
                </tr>

                <tr v-if="dataset.file_name">
                    <td>Full Path:</td>
                    <td id="file_name">{{ dataset.file_name }}</td>
                </tr>
            </tbody>
        </table>
    </div>
</template>

<script>
import { mapCacheActions } from "vuex-cache";
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";
import { Services } from "./services";

export default {
    data() {
        return {
            decoded_history_id: undefined,
            decoded_job_id: undefined,
            decoded_copied_from_job_id: undefined,
        };
    },
    props: {
        hda_id: {
            type: String,
            required: true,
        },
        job_id: {
            type: String,
            required: true,
        },
    },
    created: function () {
        this.fetchDataset(this.hda_id);
        this.fetchJob(this.job_id);
        this.services = new Services({ root: this.root });
    },
    computed: {
        isAdmin: function () {
            const Galaxy = getGalaxyInstance();
            return Galaxy?.user?.isAdmin() || false;
        },
        dataset: function () {
            return this.$store.getters.dataset(this.hda_id);
        },
        job: function () {
            const job = this.$store.getters.job(this.job_id);
            return job;
        },
        isEligibleForDecode: function () {
            if (this.job.id && this.dataset.history_id && this.isAdmin) {
                this.decode_ids();
                return true;
            } else {
                return false;
            }
        },
        isCopiedFromJobId() {
            let value = false;
            if (this.job.copied_from_job_id) {
                value = true;
                if (this.isAdmin) {
                    this.decode_copied_from_job_id();
                }
            }
            return value;
        },
    },
    methods: {
        decode_ids: async function () {
            this.decoded_history_id = await this.decode(this.dataset.history_id);
            this.decoded_job_id = await this.decode(this.job.id);
        },
        decode_copied_from_job_id: async function () {
            this.decoded_copied_from_job_id = await this.decode(this.job.copied_from_job_id);
        },
        getAppRoot() {
            return getAppRoot();
        },
        decode: async function (id) {
            const response = await this.services.decode(id);
            return response.data.decoded_id;
        },
        ...mapCacheActions(["fetchJob", "fetchDataset"]),
    },
};
</script>

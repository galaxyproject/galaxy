<template>
    <div>
        <h3>Job Information</h3>
        <table id="job-information" class="tabletip">
            <tr v-if="jobInformation">
                <td>Galaxy Tool ID:</td>
                <td id="galaxy-tool-id">{{ jobInformation.tool_id }}</td>
            </tr>
            <tr v-if="jobInformation">
                <td>Galaxy Tool Version:</td>
                <td id="galaxy-tool-version">{{ jobInformation.tool_version }}</td>
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

            <tr v-if="jobInformation">
                <td>Tool Exit Code:</td>
                <td id="exist-code">{{ jobInformation.exit_code }}</td>
            </tr>

            <tr
                id="job-messages"
                v-if="jobInformation && jobInformation.job_messages && jobInformation.job_messages.length > 0"
            >
                <td>Job Messages</td>
                <td>
                    <ul style="padding-left: 15px; margin-bottom: 0px;">
                        <li v-for="message in jobInformation.job_messages" :key="message">{{ message }}</li>
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

            <tr v-if="jobInformation">
                <td>Job API ID:</td>
                <td>
                    <div id="encoded-job-id">{{ jobInformation.encoded_id }}</div>
                    <div id="job-id" v-if="jobInformation.id">{{ jobInformation.id }}</div>
                </td>
            </tr>
            <tr v-if="jobInformation && jobInformation.encoded_copied_from_job_id">
                <td>Copied from Job API ID:</td>
                <td>
                    <div id="encoded-copied-from-job-id">{{ jobInformation.encoded_copied_from_job_id }}</div>
                    <div id="copied-from-job-id" v-if="jobInformation.copied_from_job_id">
                        ({{ jobInformation.copied_from_job_id }})
                    </div>
                </td>
            </tr>

            <tr v-if="dataset.history_id">
                <td>History API ID:</td>
                <td>
                    <div id="history_id">{{ dataset.history_id }}</div>
                    <div v-if="decoded_history_id">({{ decoded_history_id }})</div>
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
            decoded_history_id: false,
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
        this.fetchJobInformation(this.job_id);
        this.services = new Services({ root: this.root });
    },
    mounted() {
        if (this.isAdmin) {
            this.decoded_history_id = this.decode(this.dataset.history_id);
        }
    },
    computed: {
        isAdmin: function () {
            const Galaxy = getGalaxyInstance();
            if (Galaxy && Galaxy.user) {
                return Galaxy.user.isAdmin();
            } else return false;
        },
        dataset: function () {
            return this.$store.getters.dataset(this.hda_id);
        },
        jobInformation: function () {
            return this.$store.getters.jobInformation(this.job_id);
        },
    },
    methods: {
        getAppRoot() {
            return getAppRoot();
        },
        decode(id) {
            this.services.decode(id).then((decoded) => {
                return decoded;
            });
        },
        ...mapCacheActions(["fetchJobInformation", "fetchDataset"]),
    },
};
</script>

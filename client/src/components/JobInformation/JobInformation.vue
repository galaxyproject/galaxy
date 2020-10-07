<template>
    <div>
        <h3>Job Information</h3>
        <table class="tabletip">
            <tr v-if="jobInformation">
                <td>Galaxy Tool ID:</td>
                <td>{{ jobInformation.tool_id }}</td>
            </tr>
            <tr v-if="jobInformation">
                <td>Galaxy Tool Version:</td>
                <td>{{ jobInformation.tool_version }}</td>
            </tr>
            <tr v-if="dataset.tool_version">
                <td>Tool Version:</td>
                <td>{{ dataset.tool_version }}</td>
            </tr>
            <tr>
                <td>Tool Standard Output:</td>
                <td><a :href="`${getAppRoot()}datasets/${this.dataset.id}/stdout`">stdout</a></td>
            </tr>
            <tr>
                <td>Tool Standard Error:</td>
                <td><a :href="`${getAppRoot()}datasets/${this.dataset.id}/stderr`">stderr</a></td>
            </tr>

            <tr v-if="jobInformation">
                <td>Tool Exit Code:</td>
                <td>{{ jobInformation.exit_code }}</td>
            </tr>

            <tr v-if="jobInformation && jobInformation.job_messages && jobInformation.job_messages.length > 0">
                <td>Job Messages</td>
                <td>
                    <ul style="padding-left: 15px; margin-bottom: 0px;">
                        <li v-for="message in jobInformation.job_messages">{{ message }}</li>
                    </ul>
                </td>
            </tr>

            <tr>
                <td>History Content API ID:</td>
                <td>
                    {{ dataset.id }}
                    <div v-if="dataset.dataset_id">({{ dataset.dataset_id }})</div>
                </td>
            </tr>

            <tr v-if="jobInformation">
                <td>Job API ID:</td>
                <td>
                    {{ jobInformation.encoded_id }}
                    <div v-if="jobInformation.id">{{ jobInformation.id }}</div>
                </td>
            </tr>
            <tr v-if="jobInformation && jobInformation.encoded_copied_from_job_id">
                <td>Copied from Job API ID:</td>
                <td>
                    {{ jobInformation.encoded_copied_from_job_id }}
                    <div v-if="jobInformation.copied_from_job_id">({{ jobInformation.copied_from_job_id }})</div>
                </td>
            </tr>
            <tr v-if="jobInformation && jobInformation.encoded_copied_from_job_id">
                <td>Copied from Job API ID:</td>
                <td>
                    {{ jobInformation.encoded_copied_from_job_id }}
                    <div v-if="jobInformation.copied_from_job_id">({{ jobInformation.copied_from_job_id }})</div>
                </td>
            </tr>
            <tr>
                <td>History API ID:</td>
                <td>
                    {{ dataset.id }}
                    <!--             TODO admin-->
                    <!--            %if trans.user_is_admin:-->
                    <!--                 (${hda.history_id})-->
                    <!--           %endif-->
                </td>
            </tr>

            <tr v-if="dataset.uuid">
                <td>UUID:</td>
                <td>{{ dataset.uuid }}</td>
            </tr>

            <tr v-if="dataset.file_name">
                <td>Full Path:</td>
                <td>{{ dataset.file_name }}</td>
            </tr>
        </table>
    </div>
</template>

<script>
import { mapCacheActions } from "vuex-cache";
import { getAppRoot } from "onload/loadConfig";

export default {
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
    },
    computed: {
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
        ...mapCacheActions(["fetchJobInformation", "fetchDataset"]),
    },
};
</script>

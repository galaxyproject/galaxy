<template>
    <b-form @submit="submit">
        <b-card title="Import Workflow">
            <b-alert :show="hasErrorMessage" variant="danger">{{ errorMessage }}</b-alert>
            <p>Please provide a Galaxy workflow export URL or a workflow file.</p>
            <b-form-group label="Archived Workflow URL">
                <b-form-input id="workflow-import-url-input" v-model="sourceURL" type="url" />
                If the workflow is accessible via a URL, enter the URL above and click Import.
            </b-form-group>
            <b-form-group label="Archived Workflow File">
                <b-form-file v-model="sourceFile" :accept="acceptedWorkflowFormats" />
                If the workflow is in a file on your computer, choose it and then click Import.
            </b-form-group>
            <b-button
                id="workflow-import-button"
                type="submit"
                :disabled="isImportDisabled"
                :title="importTooltip"
                variant="primary">
                Import workflow
            </b-button>
            <div class="mt-4">
                <h4>Import a Workflow from Configured GA4GH Tool Registry Servers (e.g. Dockstore)</h4>
                Use either the Galaxy <a :href="trsSearchHref">search form</a> or
                <a :href="trsImportHref">import from a TRS ID</a>.
            </div>
            <div class="mt-4">
                <h4>Import a Workflow from myExperiment</h4>
                <a :href="myexperiment_target_url">Visit myExperiment</a>
                <div class="form-text">Click the link above to visit myExperiment and search for Galaxy workflows.</div>
            </div>
        </b-card>
    </b-form>
</template>
<script>
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";
import axios from "axios";
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import { redirectOnImport } from "./utils";

Vue.use(BootstrapVue);

export default {
    data() {
        const Galaxy = getGalaxyInstance();
        return {
            sourceFile: null,
            sourceURL: null,
            errorMessage: null,
            myexperiment_target_url: `http://${Galaxy.config.myexperiment_target_url}/galaxy?galaxy_url=${window.location.protocol}//${window.location.host}`,
            acceptedWorkflowFormats: ".ga, .yml",
        };
    },
    computed: {
        hasErrorMessage() {
            return this.errorMessage != null;
        },
        trsSearchHref() {
            return `${getAppRoot()}workflows/trs_search`;
        },
        trsImportHref() {
            return `${getAppRoot()}workflows/trs_import`;
        },
        isImportDisabled() {
            return !this.sourceFile && !this.sourceURL;
        },
        importTooltip() {
            return this.isImportDisabled
                ? "You must provide a workflow archive URL or file."
                : this.sourceURL
                ? "Import workflow from URL"
                : "Import workflow from File";
        },
    },
    methods: {
        submit: function (ev) {
            ev.preventDefault();
            const formData = new FormData();
            formData.append("archive_file", this.sourceFile);
            formData.append("archive_source", this.sourceURL);
            axios
                .post(`${getAppRoot()}api/workflows`, formData)
                .then((response) => {
                    redirectOnImport(getAppRoot(), response.data);
                })
                .catch((error) => {
                    const message = error.response.data && error.response.data.err_msg;
                    this.errorMessage = message || "Import failed for an unknown reason.";
                });
        },
    },
};
</script>

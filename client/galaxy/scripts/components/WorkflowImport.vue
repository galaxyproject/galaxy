<template>
    <b-form @submit="submit">
        <b-card title="Import Workflow">
            <b-alert :show="hasErrorMessage" variant="danger">{{ errorMessage }}</b-alert>
            <p>Please provide a Galaxy workflow export URL or a workflow file.</p>
            <b-form-group label="Archived Workflow URL">
                <b-form-input id="workflow-import-url-input" type="url" v-model="sourceURL" />
                If the workflow is accessible via a URL, enter the URL above and click Import.
            </b-form-group>
            <b-form-group label="Archived Workflow File">
                <b-form-file v-model="sourceFile" />
                If the workflow is in a file on your computer, choose it and then click Import.
            </b-form-group>
            <b-button id="workflow-import-button" type="submit">Import workflow</b-button>
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

Vue.use(BootstrapVue);

export default {
    data() {
        let Galaxy = getGalaxyInstance();
        return {
            sourceFile: null,
            sourceURL: null,
            errorMessage: null,
            myexperiment_target_url: `http://${Galaxy.config.myexperiment_target_url}/galaxy?galaxy_url=${
                window.location.protocol
            }//${window.location.host}`
        };
    },
    computed: {
        hasErrorMessage() {
            return this.errorMessage != null;
        }
    },
    methods: {
        submit: function(ev) {
            ev.preventDefault();
            if (!this.sourceFile && !this.sourceURL) {
                this.errorMessage = "You must provide a workflow archive URL or file.";
            } else {
                let formData = new FormData();
                formData.append("archive_file", this.sourceFile);
                formData.append("archive_source", this.sourceURL);
                axios
                    .post(`${getAppRoot()}api/workflows`, formData)
                    .then(response => {
                        window.location = `${getAppRoot()}workflows/list?message=${
                            response.data.message
                        }&status=success`;
                    })
                    .catch(error => {
                        let message = error.response.data && error.response.data.err_msg;
                        this.errorMessage = message || "Import failed for an unknown reason.";
                    });
            }
        }
    }
};
</script>

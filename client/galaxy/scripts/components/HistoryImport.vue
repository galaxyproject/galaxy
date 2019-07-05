<template>
    <b-form @submit="submit">
        <b-card title="Import a history from an archive">
            <b-alert :show="hasErrorMessage" variant="danger">{{ errorMessage }}</b-alert>
            <p>Please provide a Galaxy history export URL or a history file.</p>
            <b-form-group label="Archived History URL"> <b-form-input type="url" v-model="sourceURL" /> </b-form-group>
            <b-form-group label="Archived History File"> <b-form-file v-model="sourceFile" /> </b-form-group>
            <b-button type="submit">Import history</b-button>
        </b-card>
    </b-form>
</template>
<script>
import { getAppRoot } from "onload/loadConfig";
import axios from "axios";
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";

Vue.use(BootstrapVue);

export default {
    data() {
        return {
            sourceFile: null,
            sourceURL: null,
            errorMessage: null
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
                this.errorMessage = "You must provide a history archive URL or file.";
            } else {
                let formData = new FormData();
                formData.append("archive_file", this.sourceFile);
                formData.append("archive_source", this.sourceURL);
                axios
                    .post(`${getAppRoot()}api/histories`, formData)
                    .then(response => {
                        window.location = `${getAppRoot()}histories/list?message=${
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

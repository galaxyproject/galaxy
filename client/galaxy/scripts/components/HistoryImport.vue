<template>
    <div class="ui-portlet-limited">
        <div class="portlet-header">
            <div class="portlet-title">
                <i class="portlet-title-icon fa fa-upload"></i>
                <span class="portlet-title-text"><b>Import a History from an Archive</b></span>
            </div>
        </div>
        <div class="portlet-content">
            <b-form @submit="submit">
                <b-alert class="ui-message visible d-block" :show="hasErrorMessage" variant="danger">{{ errorMessage }}</b-alert>
                <div class="ui-form-element">
                    <div class="ui-form-title">Archived History URL</div>
                    <b-form-input type="url" v-model="sourceURL"/>
                </div>
                <div class="ui-form-element">
                    <div class="ui-form-title">Archived History file</div>
                    <b-form-file v-model="sourceFile"/>
                </div>
                <div class="portlet-buttons">
                    <b-button type="submit">Import history</b-button>
                </div>
            </b-form>
        </div>
    </div>
</template>
<script>
import axios from "axios";

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
                    .post(`${Galaxy.root}api/histories`, formData)
                    .then(response => {
                        window.location = `${Galaxy.root}histories/list?message=${response.message}&status=success`;
                    })
                    .catch(response => {
                        let message = response.responseJSON && response.responseJSON.err_msg;
                        this.errorMessage = message || "Import failed for unkown reason.";
                    });
            }
        }
    }
};
</script>

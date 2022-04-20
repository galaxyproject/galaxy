<template>
    <div class="export-to-remote-file">
        <b-alert v-if="errorMessage" show variant="danger" dismissible @dismissed="errorMessage = null">
            {{ errorMessage }}
            <JobError
                v-if="jobError"
                style="margin-top: 15px"
                header="History export job ended in error"
                :job="jobError" />
        </b-alert>
        <div v-if="waitingOnJob">
            <loading-span message="Executing history export job, this will likely take a while." />
        </div>
        <div v-else-if="jobComplete">
            <b-alert show variant="success" dismissible @dismissed="reset">
                <h4>Done!</h4>
                <p>History successfully exported.</p>
            </b-alert>
        </div>
        <div v-else>
            <b-form-group
                id="fieldset-directory"
                label-for="directory"
                description="Select a 'remote files' directory to export history archive to."
                class="mt-3">
                <files-input id="directory" v-model="directory" mode="directory" :require-writable="true" />
            </b-form-group>
            <b-form-group id="fieldset-name" label-for="name" description="Give the exported file a name." class="mt-3">
                <b-form-input id="name" v-model="name" placeholder="Name" required></b-form-input>
            </b-form-group>
            <b-row align-h="end">
                <b-col
                    ><b-button class="export-button" variant="primary" @click="doExport" :disabled="!canExport"
                        >Export</b-button
                    ></b-col
                >
            </b-row>
        </div>
    </div>
</template>

<script>
import { getAppRoot } from "onload/loadConfig";
import axios from "axios";
import { waitOnJob } from "components/JobStates/wait";
import { errorMessageAsString } from "utils/simple-error";
import LoadingSpan from "components/LoadingSpan";
import FilesInput from "components/FilesDialog/FilesInput.vue";
import JobError from "components/JobInformation/JobError";
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
Vue.use(BootstrapVue);

export default {
    components: {
        FilesInput,
        LoadingSpan,
        JobError,
    },
    props: {
        historyId: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            errorMessage: null,
            name: null,
            directory: null,
            waitingOnJob: false,
            jobComplete: false,
            jobError: null,
        };
    },
    computed: {
        canExport() {
            return !!this.name && !!this.directory;
        },
    },
    methods: {
        doExport() {
            const data = {
                directory_uri: this.directory,
                file_name: this.name,
            };
            this.waitingOnJob = true;
            const url = `${getAppRoot()}api/histories/${this.historyId}/exports`;
            axios
                .put(url, data)
                .then((response) => {
                    waitOnJob(response.data.job_id)
                        .then((data) => {
                            this.waitingOnJob = false;
                            this.jobComplete = true;
                        })
                        .catch(this.handleError);
                })
                .catch(this.handleError);
        },
        reset() {
            this.jobComplete = false;
            this.errorMessage = null;
            this.name = "";
            this.directory = "";
            this.jobError = null;
        },
        handleError(err) {
            this.waitingOnJob = false;
            this.errorMessage = errorMessageAsString(err, "History export failed.");
            if (err?.data?.stderr) {
                this.jobError = err.data;
            }
        },
    },
};
</script>

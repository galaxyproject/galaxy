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
            <LoadingSpan message="Executing history export job, this will likely take a while." />
        </div>
        <div v-else-if="jobComplete">
            <b-alert show variant="success" dismissible @dismissed="reset">
                <h2 class="h-sm">Done!</h2>
                <p>History successfully exported.</p>
            </b-alert>
        </div>
        <ExportForm v-else what="history archive" @export="doExport" />
    </div>
</template>

<script>
import axios from "axios";
import BootstrapVue from "bootstrap-vue";
import ExportForm from "components/Common/ExportForm";
import JobError from "components/JobInformation/JobError";
import { waitOnJob } from "components/JobStates/wait";
import LoadingSpan from "components/LoadingSpan";
import { getAppRoot } from "onload/loadConfig";
import { errorMessageAsString } from "utils/simple-error";
import Vue from "vue";

Vue.use(BootstrapVue);

export default {
    components: {
        ExportForm,
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
            waitingOnJob: false,
            jobComplete: false,
            jobError: null,
        };
    },
    methods: {
        doExport(directory, name) {
            const data = {
                directory_uri: directory,
                file_name: name,
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

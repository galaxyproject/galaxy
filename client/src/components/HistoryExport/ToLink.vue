<template>
    <div>
        <b-alert v-if="errorMessage" show variant="danger" dismissible @dismissed="errorMessage = null">
            {{ errorMessage }}
            <JobError
                v-if="jobError"
                style="margin-top: 15px"
                header="History export job ended in error"
                :job="jobError" />
        </b-alert>
        <div v-if="loadingExports">
            <LoadingSpan message="Loading history export information from Galaxy server." />
        </div>
        <div v-else-if="waitingOnJob">
            <LoadingSpan message="Galaxy server is preparing history for download, this will likely take a while." />
        </div>
        <div v-else-if="latestExportReady">
            Link for download ready
            <ExportLink :history-export="latestExport" />
            <p>Use this link to download the archive or import it on another Galaxy server.</p>
            <b-alert show variant="warning"
                >History archives are removed at regular intervals. For permanent storage download the archive, export
                to a repository or import the archive on another Galaxy server.
            </b-alert>
        </div>
        <div v-else-if="hasReadyExport">
            <p>An out of date export is ready <ExportLink :history-export="latestReadyExport" />.</p>

            <p>
                The history has changed since this export was generated,
                <a class="export-link" href="#" @click.prevent="regenerateExport"
                    >click here to generate a new archive for the current history state</a
                >.
            </p>
        </div>
        <div v-else>
            <p>No link for history export ready, {{ whyNoLink }}.</p>
            <p>
                <b
                    ><a class="export-link" href="#" @click.prevent="regenerateExport"
                        >Click here to generate a new archive for this history.</a
                    ></b
                >
            </p>
        </div>
    </div>
</template>

<script>
import axios from "axios";
import BootstrapVue from "bootstrap-vue";
import JobError from "components/JobInformation/JobError";
import { waitOnJob } from "components/JobStates/wait";
import LoadingSpan from "components/LoadingSpan";
import { getAppRoot } from "onload/loadConfig";
import { errorMessageAsString } from "utils/simple-error";
import Vue from "vue";

import ExportLink from "./ExportLink.vue";

Vue.use(BootstrapVue);

export default {
    components: { LoadingSpan, ExportLink, JobError },
    props: {
        historyId: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            errorMessage: null,
            exportsInitialized: false,
            exports: null,
            loadingExports: false,
            waitingOnJob: false,
            jobError: null,
        };
    },
    computed: {
        hasExports() {
            return this.exports !== null && this.exports.length > 0;
        },
        latestExport() {
            return this.exports && this.exports[0];
        },
        readyExports() {
            return (this.exports || []).filter((e) => e.ready);
        },
        hasReadyExport() {
            return this.latestReadyExport !== null;
        },
        latestReadyExport() {
            return this.readyExports.length > 0 ? this.readyExports[0] : null;
        },
        latestExportReady() {
            return this.latestExport?.ready && this.latestExport?.up_to_date;
        },
        latestExportPreparing() {
            return this.latestExport?.preparing;
        },
        whyNoLink() {
            if (!this.hasExports) {
                return `no history export ever initiated for this history`;
            } else {
                return `previous history export archival likely failed`;
            }
        },
    },
    created() {
        if (!this.exportsInitialized) {
            this.exportsInitialized = true;
            this.loadExports();
        }
    },
    methods: {
        loadExports() {
            this.loadingExports = true;
            const url = `${getAppRoot()}api/histories/${this.historyId}/exports`;
            axios
                .get(url)
                .then((response) => {
                    this.loadingExports = false;
                    this.exports = response.data;
                    if (this.latestExportPreparing) {
                        this.waitOnExportJob(this.latestExport.job_id);
                    } else {
                        this.waitingOnJob = false;
                    }
                })
                .catch(this.handleError);
        },
        regenerateExport() {
            this.waitingOnJob = true;
            const url = `${getAppRoot()}api/histories/${this.historyId}/exports`;
            axios
                .put(url)
                .then((response) => {
                    const status = response.status;
                    if (status == 200) {
                        this.loadExports();
                    } else if (status == 202) {
                        this.waitOnExportJob(response.data.job_id);
                    } else {
                        // error ....
                        this.errorMessage = `Unexpected error while polling history export ${errorMessageAsString(
                            response
                        )}`;
                    }
                })
                .catch(this.handleError);
        },
        waitOnExportJob(jobId) {
            this.waitingOnJob = true;
            this.jobError = false;
            waitOnJob(jobId)
                .then((jobResponse) => {
                    this.waitingOnJob = false;
                    this.loadExports();
                })
                .catch(this.handleError);
        },
        handleError(err) {
            this.waitingOnJob = false;
            this.loadingExports = false;
            this.errorMessage = errorMessageAsString(err, "Error generating a history export link");
            if (err?.data?.stderr) {
                this.jobError = err.data;
            }
        },
    },
};
</script>

<template>
    <b-card body-class="history-import-component" title="Import a history from an archive">
        <b-alert v-if="errorMessage" variant="danger" dismissible show @dismissed="errorMessage = null">
            {{ errorMessage }}
            <JobError
                v-if="jobError"
                style="margin-top: 15px"
                header="History import job ended in error"
                :job="jobError" />
        </b-alert>
        <div v-if="initializing">
            <loading-span message="Loading server configuration." />
        </div>
        <div v-else-if="waitingOnJob">
            <LoadingSpan message="Waiting on history import job, this may take a while." />
        </div>
        <div v-else-if="complete">
            <b-alert :show="complete" variant="success" dismissible @dismissed="complete = false">
                <h4>Done!</h4>
                <p>History imported, check out <a :href="historyLink">your histories</a>.</p>
            </b-alert>
        </div>
        <div v-else>
            <b-form @submit.prevent="submit">
                <b-form-group v-slot="{ ariaDescribedby }" label="How would you like to specify the history archive?">
                    <b-form-radio-group
                        v-model="importType"
                        :aria-describedby="ariaDescribedby"
                        name="import-type"
                        stacked>
                        <b-form-radio value="externalUrl">
                            Export URL from another Galaxy instance
                            <font-awesome-icon icon="external-link-alt" />
                        </b-form-radio>
                        <b-form-radio value="upload">
                            Upload local file from your computer
                            <font-awesome-icon icon="upload" />
                        </b-form-radio>
                        <b-form-radio v-if="hasFileSources" value="remoteFilesUri">
                            Select a remote file (e.g. Galaxy's FTP)
                            <font-awesome-icon icon="folder-open" />
                        </b-form-radio>
                    </b-form-radio-group>
                </b-form-group>
                <b-form-group v-if="importType == 'externalUrl'" label="Archived History URL">
                    <b-form-input v-model="sourceURL" type="url" />
                </b-form-group>
                <b-form-group v-if="importType == 'upload'" label="Archived History File">
                    <b-form-file v-model="sourceFile" />
                </b-form-group>
                <b-form-group v-show="importType == 'remoteFilesUri'" label="Remote File">
                    <!-- using v-show so we can have a persistent ref and launch dialog on select -->
                    <files-input ref="filesInput" v-model="sourceRemoteFilesUri" />
                </b-form-group>
                <b-button class="import-button" variant="primary" type="submit" :disabled="!importReady"
                    >Import history</b-button
                >
            </b-form>
        </div>
    </b-card>
</template>
<script>
import { getAppRoot } from "onload/loadConfig";
import axios from "axios";
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faFolderOpen, faUpload, faExternalLinkAlt } from "@fortawesome/free-solid-svg-icons";
import FilesInput from "components/FilesDialog/FilesInput.vue";
import { waitOnJob } from "components/JobStates/wait";
import { errorMessageAsString } from "utils/simple-error";
import LoadingSpan from "components/LoadingSpan";
import JobError from "components/JobInformation/JobError";
import { Services } from "components/FilesDialog/services";

library.add(faFolderOpen);
library.add(faUpload);
library.add(faExternalLinkAlt);
Vue.use(BootstrapVue);

export default {
    components: { FilesInput, FontAwesomeIcon, JobError, LoadingSpan },
    data() {
        return {
            initializing: true,
            importType: "externalUrl",
            sourceFile: null,
            sourceURL: null,
            sourceRemoteFilesUri: null,
            errorMessage: null,
            waitingOnJob: false,
            complete: false,
            jobError: null,
            hasFileSources: false,
        };
    },
    computed: {
        importReady() {
            const importType = this.importType;
            if (importType == "externalUrl") {
                return !!this.sourceURL;
            } else if (importType == "upload") {
                return !!this.sourceFile;
            } else if (importType == "remoteFilesUri") {
                return !!this.sourceRemoteFilesUri;
            } else {
                return false;
            }
        },
        historyLink() {
            return `${getAppRoot()}histories/list`;
        },
    },
    watch: {
        importType() {
            if (this.importType == "remoteFilesUri" && !this.sourceRemoteFilesUri) {
                this.$refs.filesInput.selectFile();
            }
        },
    },
    async mounted() {
        await this.initialize();
    },
    methods: {
        async initialize() {
            const fileSources = await new Services().getFileSources();
            this.hasFileSources = fileSources.length > 0;
            this.initializing = false;
        },
        submit: function (ev) {
            const formData = new FormData();
            const importType = this.importType;
            if (importType == "externalUrl") {
                formData.append("archive_source", this.sourceURL);
            } else if (importType == "upload") {
                formData.append("archive_file", this.sourceFile);
                formData.append("archive_source", "");
            } else if (importType == "remoteFilesUri") {
                formData.append("archive_source", this.sourceRemoteFilesUri);
            }
            axios
                .post(`${getAppRoot()}api/histories`, formData)
                .then((response) => {
                    this.waitingOnJob = true;
                    waitOnJob(response.data.id)
                        .then((jobResponse) => {
                            this.waitingOnJob = false;
                            this.complete = true;
                        })
                        .catch(this.handleError);
                })
                .catch(this.handleError);
        },
        handleError: function (err) {
            this.waitingOnJob = false;
            this.errorMessage = errorMessageAsString(err, "History import failed.");
            if (err?.data?.stderr) {
                this.jobError = err.data;
            }
        },
    },
};
</script>

<style scoped>
.error-wrapper {
    margin-top: 10px;
}
</style>

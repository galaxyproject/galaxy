<template>
    <div class="history-import-component" aria-labelledby="history-import-heading">
        <h1 id="history-import-heading" class="h-lg">
            Import {{ identifierText === "invocation" ? "an" : "a" }} {{ identifierText }} from an archive
        </h1>

        <b-alert v-if="errorMessage" variant="danger" dismissible show @dismissed="errorMessage = null">
            {{ errorMessage }}
            <JobError
                v-if="jobError"
                style="margin-top: 15px"
                :header="`${identifierTextCapitalized} import job ended in error`"
                :job="jobError" />
        </b-alert>

        <div v-if="initializing">
            <LoadingSpan message="Loading server configuration." />
        </div>
        <div v-else-if="waitingOnJob">
            <LoadingSpan :message="`Waiting on ${identifierText} import job, this may take a while.`" />
        </div>
        <div v-else-if="complete">
            <ImportSuccess
                v-if="jobId"
                :job-id="jobId"
                :link-to-list="linkToList"
                :identifier-text-plural="identifierTextPlural"
                :identifier-text-capitalized="identifierTextCapitalized" />
        </div>
        <div v-else>
            <b-form @submit.prevent="submit">
                <b-form-group v-slot="{ ariaDescribedby }" :label="howLabel">
                    <b-form-radio-group
                        v-model="importType"
                        :aria-describedby="ariaDescribedby"
                        name="import-type"
                        stacked>
                        <b-form-radio value="externalUrl">
                            Export URL from another Galaxy instance
                            <FontAwesomeIcon icon="external-link-alt" />
                        </b-form-radio>
                        <b-form-radio value="upload">
                            Upload local file from your computer
                            <FontAwesomeIcon icon="upload" />
                        </b-form-radio>
                        <b-form-radio v-if="hasFileSources" value="remoteFilesUri">
                            Select a repository (e.g. Galaxy's FTP)
                            <FontAwesomeIcon icon="folder-open" />
                        </b-form-radio>
                    </b-form-radio-group>
                </b-form-group>

                <b-form-group v-if="invocationImport" v-slot="{ ariaDescribedby }" :label="whereLabel">
                    <b-form-radio-group
                        v-model="importTarget"
                        :aria-describedby="ariaDescribedby"
                        name="import-target"
                        stacked>
                        <b-form-radio value="newHistory"> Import into a new history. </b-form-radio>
                        <b-form-radio value="currentHistory"> Import into the current history. </b-form-radio>
                    </b-form-radio-group>
                </b-form-group>

                <b-form-group v-if="importType === 'externalUrl'" :label="urlLabel">
                    <b-alert v-if="showImportUrlWarning" variant="warning" show>
                        It looks like you are trying to import a published history from another galaxy instance. You can
                        only import histories via an archive URL.
                        <ExternalLink
                            href="https://training.galaxyproject.org/training-material/faqs/galaxy/histories_transfer_entire_histories_from_one_galaxy_server_to_another.html">
                            Read more on the GTN
                        </ExternalLink>
                    </b-alert>

                    <b-form-input v-model="sourceURL" type="url" />
                </b-form-group>
                <b-form-group v-else-if="importType === 'upload'" :label="fileLabel">
                    <b-form-file v-model="sourceFile" />
                </b-form-group>
                <b-form-group v-show="importType === 'remoteFilesUri'" label="Repository">
                    <!-- using v-show so we can have a persistent ref and launch dialog on select -->
                    <FilesInput ref="filesInput" v-model="sourceRemoteFilesUri" />
                </b-form-group>

                <GButton class="import-button" color="blue" type="submit" :disabled="!importReady">
                    Import {{ identifierText }}
                </GButton>
            </b-form>
        </div>
    </div>
</template>

<script>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faExternalLinkAlt, faFolderOpen, faUpload } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { refDebounced } from "@vueuse/core";
import axios from "axios";
import BootstrapVue from "bootstrap-vue";
import ImportSuccess from "components/ImportSuccess";
import JobError from "components/JobInformation/JobError";
import { waitOnJob } from "components/JobStates/wait";
import LoadingSpan from "components/LoadingSpan";
import { getAppRoot } from "onload/loadConfig";
import { errorMessageAsString } from "utils/simple-error";
import { capitalizeFirstLetter } from "utils/strings";
import Vue, { ref, watch } from "vue";

import { fetchFileSources } from "@/api/remoteFiles";

import ExternalLink from "./ExternalLink";

import GButton from "./BaseComponents/GButton.vue";
import FilesInput from "components/FilesDialog/FilesInput.vue";

library.add(faFolderOpen);
library.add(faUpload);
library.add(faExternalLinkAlt);
Vue.use(BootstrapVue);

export default {
    components: { FilesInput, FontAwesomeIcon, ImportSuccess, JobError, LoadingSpan, ExternalLink, GButton },
    props: {
        invocationImport: {
            type: Boolean,
            default: false,
        },
    },
    setup() {
        const sourceURL = ref("");
        const debouncedURL = refDebounced(sourceURL, 200);
        const mayBeHistoryUrlRegEx = /\/u(ser)?\/.+\/h(istory)?\/.+/;

        const showImportUrlWarning = ref(false);

        watch(
            () => debouncedURL.value,
            (val) => {
                const url = val ?? "";
                showImportUrlWarning.value = Boolean(url.match(mayBeHistoryUrlRegEx));
            }
        );

        return {
            sourceURL,
            showImportUrlWarning,
        };
    },
    data() {
        return {
            initializing: true,
            importType: "externalUrl",
            importTarget: "newHistory", // "newHistory" or "currentHistory" - where to do import (if invocation)
            sourceFile: null,
            sourceRemoteFilesUri: "",
            errorMessage: null,
            waitingOnJob: false,
            complete: false,
            jobError: null,
            jobId: null,
            hasFileSources: false,
        };
    },
    computed: {
        howLabel() {
            return `How would you like to specify the ${this.identifierText} archive?`;
        },
        whereLabel() {
            return `Where would you like to import the ${this.identifierText} archive?`;
        },
        urlLabel() {
            return `Archived ${this.identifierTextCapitalized} URL`;
        },
        fileLabel() {
            return `Archived ${this.identifierTextCapitalized} File`;
        },
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
        linkToList() {
            return this.invocationImport ? `/workflows/invocations` : `/histories/list`;
        },
        identifierText() {
            return this.invocationImport ? "invocation" : "history";
        },
        identifierTextCapitalized() {
            return capitalizeFirstLetter(this.identifierText);
        },
        identifierTextPlural() {
            return this.invocationImport ? "invocations" : "histories";
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
            const fileSources = await fetchFileSources();
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
            if (this.importTarget == "newHistory") {
                formData.append("name", "History for Workflow Import");
            }
            axios
                .post(`${getAppRoot()}api/histories`, formData)
                .then((response) => {
                    this.waitingOnJob = true;
                    this.jobId = response.data.id;
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

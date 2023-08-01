<template>
    <div class="history-import-component" aria-labelledby="history-import-heading">
        <h1 id="history-import-heading" class="h-lg">Import a history from an archive</h1>

        <GAlert v-if="errorMessage" variant="danger" dismissible show @dismissed="errorMessage = null">
            {{ errorMessage }}
            <JobError
                v-if="jobError"
                style="margin-top: 15px"
                header="History import job ended in error"
                :job="jobError" />
        </GAlert>

        <div v-if="initializing">
            <LoadingSpan message="Loading server configuration." />
        </div>
        <div v-else-if="waitingOnJob">
            <LoadingSpan message="Waiting on history import job, this may take a while." />
        </div>
        <div v-else-if="complete">
            <GAlert :show="complete" variant="success" dismissible @dismissed="complete = false">
                <span class="mb-1 h-sm">Done!</span>
                <p>History imported, check out <a :href="historyLink">your histories</a>.</p>
            </GAlert>
        </div>
        <div v-else>
            <b-form @submit.prevent="submit">
                <GFormGroup v-slot="{ ariaDescribedby }" label="How would you like to specify the history archive?">
                    <GFormRadioGroup
                        v-model="importType"
                        :aria-describedby="ariaDescribedby"
                        name="import-type"
                        stacked>
                        <GFormRadio value="externalUrl">
                            Export URL from another Galaxy instance
                            <FontAwesomeIcon icon="external-link-alt" />
                        </GFormRadio>
                        <GFormRadio value="upload">
                            Upload local file from your computer
                            <FontAwesomeIcon icon="upload" />
                        </GFormRadio>
                        <GFormRadio v-if="hasFileSources" value="remoteFilesUri">
                            Select a remote file (e.g. Galaxy's FTP)
                            <FontAwesomeIcon icon="folder-open" />
                        </GFormRadio>
                    </GFormRadioGroup>
                </GFormGroup>

                <GFormGroup v-if="importType === 'externalUrl'" label="Archived History URL">
                    <GAlert v-if="showImportUrlWarning" variant="warning" show>
                        It looks like you are trying to import a published history from another galaxy instance. You can
                        only import histories via an archive URL.
                        <ExternalLink
                            href="https://training.galaxyproject.org/training-material/faqs/galaxy/histories_transfer_entire_histories_from_one_galaxy_server_to_another.html">
                            Read more on the GTN
                        </ExternalLink>
                    </GAlert>

                    <GInput v-model="sourceURL" type="url" />
                </GFormGroup>
                <GFormGroup v-else-if="importType === 'upload'" label="Archived History File">
                    <GFormFile v-model="sourceFile" />
                </GFormGroup>
                <GFormGroup v-show="importType === 'remoteFilesUri'" label="Remote File">
                    <!-- using v-show so we can have a persistent ref and launch dialog on select -->
                    <FilesInput ref="filesInput" v-model="sourceRemoteFilesUri" />
                </GFormGroup>

                <GButton class="import-button" variant="primary" type="submit" :disabled="!importReady">
                    Import history
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
import JobError from "components/JobInformation/JobError";
import { waitOnJob } from "components/JobStates/wait";
import LoadingSpan from "components/LoadingSpan";
import { getAppRoot } from "onload/loadConfig";
import { errorMessageAsString } from "utils/simple-error";
import { ref, watch } from "vue";

import { GAlert, GButton, GFormFile, GFormGroup, GFormRadio, GFormRadioGroup, GInput } from "@/component-library";
import { getFileSources } from "@/components/FilesDialog/services";

import ExternalLink from "./ExternalLink";

import FilesInput from "components/FilesDialog/FilesInput.vue";

library.add(faFolderOpen);
library.add(faUpload);
library.add(faExternalLinkAlt);

export default {
    components: {
        ExternalLink,
        FilesInput,
        FontAwesomeIcon,
        GAlert,
        GButton,
        GFormFile,
        GFormGroup,
        GFormRadio,
        GFormRadioGroup,
        GInput,
        JobError,
        LoadingSpan,
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
            sourceFile: null,
            sourceRemoteFilesUri: "",
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
            const fileSources = await getFileSources();
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

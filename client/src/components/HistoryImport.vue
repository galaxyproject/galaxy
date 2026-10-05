<template>
    <div class="history-import-component" aria-labelledby="history-import-heading">
        <h1 id="history-import-heading" class="h-lg">
            Import {{ identifierText === "invocation" ? "an" : "a" }} {{ identifierText }} from an archive
        </h1>

        <GAlert v-if="errorMessage" variant="danger" dismissible show @dismissed="errorMessage = null">
            {{ errorMessage }}
            <JobError
                v-if="jobError"
                style="margin-top: 15px"
                :header="`${identifierTextCapitalized} import job ended in error`"
                :job="jobError" />
        </GAlert>

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
            <BForm @submit.prevent="submit">
                <BFormGroup v-slot="{ ariaDescribedby }" :label="howLabel">
                    <BFormRadioGroup
                        v-model="importType"
                        :aria-describedby="ariaDescribedby"
                        name="import-type"
                        stacked>
                        <BFormRadio value="externalUrl">
                            Export URL from another Galaxy instance
                            <FontAwesomeIcon :icon="faExternalLinkAlt" />
                        </BFormRadio>
                        <BFormRadio value="upload">
                            Upload local file from your computer
                            <FontAwesomeIcon :icon="faUpload" />
                        </BFormRadio>
                        <BFormRadio v-if="hasFileSources" value="remoteFilesUri">
                            Select a repository (e.g. Galaxy's FTP)
                            <FontAwesomeIcon :icon="faFolderOpen" />
                        </BFormRadio>
                    </BFormRadioGroup>
                </BFormGroup>

                <BFormGroup v-if="invocationImport" v-slot="{ ariaDescribedby }" :label="whereLabel">
                    <BFormRadioGroup
                        v-model="importTarget"
                        :aria-describedby="ariaDescribedby"
                        name="import-target"
                        stacked>
                        <BFormRadio value="newHistory"> Import into a new history. </BFormRadio>
                        <BFormRadio value="currentHistory"> Import into the current history. </BFormRadio>
                    </BFormRadioGroup>
                </BFormGroup>

                <BFormGroup v-if="importType === 'externalUrl'" :label="urlLabel">
                    <GAlert v-if="showImportUrlWarning" variant="warning" show>
                        It looks like you are trying to import a published history from another galaxy instance. You can
                        only import histories via an archive URL.
                        <ExternalLink
                            href="https://training.galaxyproject.org/training-material/faqs/galaxy/histories_transfer_entire_histories_from_one_galaxy_server_to_another.html">
                            Read more on the GTN
                        </ExternalLink>
                    </GAlert>

                    <BFormInput v-model="sourceURL" type="url" />
                </BFormGroup>
                <BFormGroup v-else-if="importType === 'upload'" :label="fileLabel">
                    <BFormFile v-model="sourceFile" />
                </BFormGroup>
                <BFormGroup v-show="importType === 'remoteFilesUri'" label="Repository">
                    <!-- using v-show so we can have a persistent ref and launch dialog on select -->
                    <FilesInput ref="filesInput" v-model="sourceRemoteFilesUri" />
                </BFormGroup>

                <GButton class="import-button" color="blue" type="submit" :disabled="!importReady">
                    Import {{ identifierText }}
                </GButton>
            </BForm>
        </div>
    </div>
</template>

<script>
import { faExternalLinkAlt, faFolderOpen, faUpload } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { refDebounced } from "@vueuse/core";
import axios from "axios";
import { BForm, BFormFile, BFormGroup, BFormInput, BFormRadio, BFormRadioGroup } from "bootstrap-vue";
import { ref, watch } from "vue";

import { fetchFileSources } from "@/api/remoteFiles";
import { waitOnJob } from "@/components/JobStates/wait";
import { getAppRoot } from "@/onload/loadConfig";
import { errorMessageAsString } from "@/utils/simple-error";
import { capitalizeFirstLetter } from "@/utils/strings";

import GAlert from "./BaseComponents/GAlert.vue";
import GButton from "./BaseComponents/GButton.vue";
import ExternalLink from "./ExternalLink.vue";
import FilesInput from "@/components/FilesDialog/FilesInput.vue";
import ImportSuccess from "@/components/ImportSuccess.vue";
import JobError from "@/components/JobInformation/JobError.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

export default {
    components: {
        BForm,
        BFormFile,
        BFormGroup,
        BFormInput,
        BFormRadio,
        BFormRadioGroup,
        FilesInput,
        FontAwesomeIcon,
        ImportSuccess,
        JobError,
        LoadingSpan,
        ExternalLink,
        GAlert,
        GButton,
    },
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
            },
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
            faExternalLinkAlt,
            faFolderOpen,
            faUpload,
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

<script setup>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faEdit, faFile, faFolderOpen, faLock } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { getGalaxyInstance } from "app";
import { BAlert, BButton } from "bootstrap-vue";
import { getRemoteEntries, getRemoteEntriesAt } from "components/Upload/utils";
import { filesDialog } from "utils/data";
import { urlData } from "utils/url";
import { computed, ref } from "vue";

import { RULES_TYPES } from "./utils.js";

import UploadSelect from "./UploadSelect.vue";

library.add(faEdit, faFile, faFolderOpen, faLock);

const props = defineProps({
    hasCallback: {
        type: Boolean,
        default: false,
    },
    fileSourcesConfigured: {
        type: Boolean,
        required: true,
    },
    ftpUploadSite: {
        type: String,
        default: null,
    },
    historyId: {
        type: String,
        required: true,
    },
});

const emit = defineEmits(["dismiss"]);

const dataType = ref("datasets");
const errorMessage = ref(null);
const ftpFiles = ref([]);
const selectedDatasetId = ref(null);
const selectionType = ref("raw");
const sourceContent = ref(null);
const uris = ref([]);

const isDisabled = computed(() => selectionType.value !== "raw");

function eventBuild() {
    const Galaxy = getGalaxyInstance();
    const entry = {
        dataType: dataType.value,
        selectionType: selectionType.value,
    };
    if (entry.selectionType == "ftp") {
        entry.elements = ftpFiles.value;
        entry.ftpUploadSite = props.ftpUploadSite;
    } else if (entry.selectionType === "raw") {
        entry.content = sourceContent.value;
    } else if (entry.selectionType == "remote_files") {
        entry.elements = uris.value;
    }
    Galaxy.currHistoryPanel.buildCollectionFromRules(entry, null, true);
    emit("dismiss");
}

function eventReset() {
    selectedDatasetId.value = null;
    selectionType.value = "raw";
    sourceContent.value = null;
}

function inputDialog() {
    const Galaxy = getGalaxyInstance();
    Galaxy.data.dialog(
        (response) => {
            selectedDatasetId.value = response.id;
            urlData({ url: `/api/histories/${props.historyId}/contents/${selectedDatasetId.value}/display` })
                .then((newSourceContent) => {
                    selectionType.value = "raw";
                    sourceContent.value = newSourceContent;
                })
                .catch((error) => {
                    errorMessage.value = error;
                });
        },
        {
            multiple: false,
            library: false,
            format: null,
            allowUpload: false,
        }
    );
}

function inputFtp() {
    getRemoteEntries((ftp_files) => {
        selectionType.value = "ftp";
        sourceContent.value = ftp_files.map((file) => file["path"]).join("\n");
        ftpFiles.value = ftp_files;
    });
}

function inputPaste() {
    selectionType.value = "raw";
    selectedDatasetId.value = null;
    sourceContent.value = null;
}

function inputRemote() {
    function handleRemoteFilesUri(record) {
        getRemoteEntriesAt(record.url).then((files) => {
            files = files.filter((file) => file["class"] == "File");
            selectionType.value = "remote_files";
            sourceContent.value = files.map((file) => file["uri"]).join("\n");
            uris.value = files;
        });
    }
    filesDialog(handleRemoteFilesUri, { mode: "directory" });
}
</script>

<template>
    <div class="upload-wrapper d-flex flex-column">
        <BAlert v-if="errorMessage" variant="danger" show>{{ errorMessage }}</BAlert>
        <div v-localize class="upload-header">Insert tabular source data to extract collection files and metadata.</div>
        <textarea
            v-model="sourceContent"
            class="upload-box upload-rule-source-content"
            placeholder="Insert tabular source data here."
            :disabled="isDisabled" />
        <FontAwesomeIcon v-if="isDisabled" class="upload-text-lock" icon="fa-lock" />
        <div class="upload-footer text-center">
            <span class="upload-footer-title">Upload type:</span>
            <UploadSelect v-model="dataType" class="rule-data-type" :options="RULES_TYPES" :searchable="false" />
        </div>
        <div class="upload-buttons d-flex justify-content-end">
            <BButton @click="inputPaste">
                <FontAwesomeIcon icon="fa-edit" />
                <span v-localize>Paste data</span>
            </BButton>
            <BButton data-description="rules dataset dialog" @click="inputDialog">
                <FontAwesomeIcon icon="fa-file" />
                <span v-localize>Choose dataset</span>
            </BButton>
            <BButton v-if="ftpUploadSite" @click="inputFtp">
                <FontAwesomeIcon icon="fa-folder-open" />
                <span v-localize>Import FTP files</span>
            </BButton>
            <BButton @click="inputRemote">
                <FontAwesomeIcon icon="fa-folder-open" />
                <span v-localize>Choose from repository</span>
            </BButton>
            <BButton
                id="btn-build"
                :disabled="!sourceContent"
                title="Build"
                :variant="sourceContent ? 'primary' : ''"
                @click="eventBuild">
                <span>Build</span>
            </BButton>
            <BButton id="btn-reset" title="Reset" :disabled="!sourceContent" @click="eventReset">
                <span>Reset</span>
            </BButton>
            <BButton id="btn-close" title="Close" @click="$emit('dismiss')">
                <span>Close</span>
            </BButton>
        </div>
    </div>
</template>

<style scoped>
.upload-rule-source-content {
    resize: none;
}
.upload-text-lock {
    bottom: 22%;
    font-size: 1.275rem;
    opacity: 0.2;
    right: 3%;
    position: absolute;
}
</style>

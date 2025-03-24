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
        <div v-localize class="upload-header">插入表格源数据以提取集合文件和元数据。</div>
        <textarea
            v-model="sourceContent"
            class="upload-box upload-rule-source-content"
            placeholder="在此处插入表格源数据。"
            :disabled="isDisabled" />
        <FontAwesomeIcon v-if="isDisabled" class="upload-text-lock" icon="fa-lock" />
        <div class="upload-footer text-center">
            <span class="upload-footer-title">上传类型：</span>
            <UploadSelect v-model="dataType" class="rule-data-type" :options="RULES_TYPES" :searchable="false" />
        </div>
        <div class="upload-buttons d-flex justify-content-end">
            <BButton @click="inputPaste">
                <FontAwesomeIcon icon="fa-edit" />
                <span v-localize>粘贴数据</span>
            </BButton>
            <BButton data-description="规则数据集对话框" @click="inputDialog">
                <FontAwesomeIcon icon="fa-file" />
                <span v-localize>选择数据集</span>
            </BButton>
            <BButton v-if="ftpUploadSite" @click="inputFtp">
                <FontAwesomeIcon icon="fa-folder-open" />
                <span v-localize>导入FTP文件</span>
            </BButton>
            <BButton @click="inputRemote">
                <FontAwesomeIcon icon="fa-folder-open" />
                <span v-localize>选择远程文件</span>
            </BButton>
            <BButton
                id="btn-build"
                :disabled="!sourceContent"
                title="构建"
                :variant="sourceContent ? 'primary' : ''"
                @click="eventBuild">
                <span>构建</span>
            </BButton>
            <BButton id="btn-reset" title="重置" :disabled="!sourceContent" @click="eventReset">
                <span>重置</span>
            </BButton>
            <BButton id="btn-close" title="关闭" @click="$emit('dismiss')">
                <span>关闭</span>
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

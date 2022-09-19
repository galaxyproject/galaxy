<template>
    <upload-wrapper ref="wrapper" :top-info="topInfo | l">
        <span style="width: 25%; display: inline; height: 100%" class="float-left">
            <div class="upload-rule-option">
                <div class="upload-rule-option-title">{{ "Upload data as" | l }}</div>
                <div class="rule-data-type">
                    <select2 v-model="dataType" container-class="upload-footer-selection">
                        <option value="datasets">Datasets</option>
                        <option value="collections">Collection(s)</option>
                    </select2>
                </div>
            </div>
            <div class="upload-rule-option">
                <div class="upload-rule-option-title">{{ "Load tabular data from" | l }}</div>
                <div class="rule-select-type">
                    <select2 v-model="selectionType" container-class="upload-footer-selection">
                        <option value="paste">{{ "Pasted Table" | l }}</option>
                        <option value="dataset">{{ "History Dataset" | l }}</option>
                        <option v-if="ftpUploadSite" value="ftp">{{ "FTP Directory" | l }}</option>
                        <option value="remote_files">{{ "Remote Files Directory" | l }}</option>
                    </select2>
                </div>
            </div>
            <div v-if="selectionType == 'dataset'" id="upload-rule-dataset-option" class="upload-rule-option">
                <div class="upload-rule-option-title">History dataset</div>
                <div>
                    <b-link v-if="selectedDatasetName == null" @click="onSelectDataset">
                        {{ "Select" | l }}
                    </b-link>
                    <span v-else>
                        {{ selectedDatasetName }} <font-awesome-icon icon="edit" @click="onSelectDataset" />
                    </span>
                </div>
            </div>
        </span>
        <span style="display: inline; float: right; width: 75%; height: 300px">
            <textarea
                v-model="sourceContent"
                class="upload-rule-source-content form-control"
                style="height: 100%"
                :disabled="selectionType != 'paste'"></textarea>
        </span>
        <template v-slot:buttons>
            <b-button
                id="btn-close"
                ref="btnClose"
                class="ui-button-default"
                :title="btnCloseTitle"
                @click="$emit('dismiss')">
                {{ btnCloseTitle | l }}
            </b-button>
            <b-button
                id="btn-build"
                ref="btnBuild"
                class="ui-button-default"
                :disabled="!sourceContent"
                :title="btnBuildTitle"
                :variant="sourceContent ? 'primary' : ''"
                @click="_eventBuild">
                {{ btnBuildTitle | l }}
            </b-button>
            <b-button
                id="btn-reset"
                ref="btnReset"
                class="ui-button-default"
                :title="btnResetTitle"
                :disabled="!enableReset"
                @click="_eventReset">
                {{ btnResetTitle | l }}
            </b-button>
        </template>
    </upload-wrapper>
</template>

<script>
import { getGalaxyInstance } from "app";
import UploadBoxMixin from "./UploadBoxMixin";
import UploadUtils from "mvc/upload/upload-utils";
import axios from "axios";
import { getAppRoot } from "onload/loadConfig";
import { filesDialog } from "utils/data";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faEdit } from "@fortawesome/free-solid-svg-icons";
import { BButton, BLink } from "bootstrap-vue";

library.add(faEdit);

export default {
    components: { BLink, BButton, FontAwesomeIcon },
    mixins: [UploadBoxMixin],
    data() {
        return {
            datasets: [],
            ftpFiles: [],
            uris: [],
            topInfo: "Tabular source data to extract collection files and metadata from",
            enableBuild: false,
            dataType: "datasets",
            selectedDatasetId: null,
            selectedDatasetName: null,
            sourceContent: "",
            selectionType: "paste",
            btnBuildTitle: "Build",
            btnResetTitle: "Reset",
        };
    },
    computed: {
        enableReset: function () {
            return this.sourceContent.length > 0;
        },
    },
    watch: {
        selectionType: function (selectionType) {
            if (selectionType == "dataset" && !this.datasetsSet) {
                this.onSelectDataset();
            } else if (selectionType == "ftp") {
                UploadUtils.getRemoteFiles((ftp_files) => {
                    this.sourceContent = ftp_files.map((file) => file["path"]).join("\n");
                    this.ftpFiles = ftp_files;
                });
            } else if (selectionType == "remote_files") {
                filesDialog(this._handleRemoteFilesUri, { mode: "directory" });
            }
        },
        selectedDatasetId: function (selectedDatasetId) {
            if (!selectedDatasetId) {
                this.sourceContent = "";
                return;
            }
            const Galaxy = getGalaxyInstance();
            axios
                .get(
                    `${getAppRoot()}api/histories/${
                        Galaxy.currHistoryPanel.model.id
                    }/contents/${selectedDatasetId}/display`,
                    // The Rule builder expects strings, we should not parse the respone to the default JSON type
                    {
                        responseType: "text",
                    }
                )
                .then((response) => {
                    this.sourceContent = response.data;
                })
                .catch((error) => console.log(error));
        },
    },
    created() {
        this.initCollection();
        this.initAppProperties();
    },
    methods: {
        _eventReset: function () {
            this.selectedDatasetId = null;
            this.sourceContent = "";
        },

        _handleRemoteFilesUri: function (record) {
            // fetch files at URI
            UploadUtils.getRemoteFilesAt(record.url).then((files) => {
                files = files.filter((file) => file["class"] == "File");
                this.sourceContent = files.map((file) => file["uri"]).join("\n");
                this.uris = files;
            });
        },

        _eventBuild: function () {
            this._buildSelection(this.sourceContent);
        },

        onSelectDataset: function () {
            const galaxy = getGalaxyInstance();
            galaxy.data.dialog(
                (response) => {
                    this.selectedDatasetId = response.id;
                    this.selectedDatasetName = response.name;
                },
                {
                    multiple: false,
                    library: false,
                    format: null,
                    allowUpload: false,
                }
            );
        },

        _buildSelection: function (content) {
            const selectionType = this.selectionType;
            const selection = {};
            const Galaxy = getGalaxyInstance();
            if (selectionType == "dataset" || selectionType == "paste") {
                selection.selectionType = "raw";
                selection.content = content;
            } else if (selectionType == "ftp") {
                selection.selectionType = "ftp";
                selection.elements = this.ftpFiles;
                selection.ftpUploadSite = this.ftpUploadSite;
            } else if (selectionType == "remote_files") {
                selection.selectionType = "remote_files";
                selection.elements = this.uris;
            }
            selection.dataType = this.dataType;
            Galaxy.currHistoryPanel.buildCollection("rules", selection, true, true);
            this.$emit("dismiss");
        },
    },
};
</script>

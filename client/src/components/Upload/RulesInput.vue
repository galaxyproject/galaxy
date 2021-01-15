<template>
    <upload-wrapper ref="wrapper" :top-info="topInfo">
        <span style="width: 25%; display: inline; height: 100%;" class="float-left">
            <div class="upload-rule-option">
                <div class="upload-rule-option-title">{{ l("Upload data as") }}</div>
                <div class="rule-data-type">
                    <select2 v-model="dataType" container-class="upload-footer-selection">
                        <option value="datasets">Datasets</option>
                        <option value="collections">Collection(s)</option>
                    </select2>
                </div>
            </div>
            <div class="upload-rule-option">
                <div class="upload-rule-option-title">{{ l("Load tabular data from") }}</div>
                <div class="rule-select-type">
                    <select2 container-class="upload-footer-selection" v-model="selectionType">
                        <option value="paste">{{ l("Pasted Table") }}</option>
                        <option value="dataset">{{ l("History Dataset") }}</option>
                        <option v-if="ftpUploadSite" value="ftp">{{ l("FTP Directory") }}</option>
                        <option value="remote_files">{{ l("Remote Files Directory") }}</option>
                    </select2>
                </div>
            </div>
            <div id="upload-rule-dataset-option" class="upload-rule-option" v-if="selectionType == 'dataset'">
                <div class="upload-rule-option-title">History dataset</div>
                <div>
                    <b-link @click="onSelectDataset" v-if="selectedDatasetName == null">
                        {{ l("Select") }}
                    </b-link>
                    <span v-else>
                        {{ selectedDatasetName }} <font-awesome-icon icon="edit" @click="onSelectDataset" />
                    </span>
                </div>
            </div>
        </span>
        <span style="display: inline; float: right; width: 75%; height: 300px;">
            <textarea
                class="upload-rule-source-content form-control"
                style="height: 100%;"
                v-model="sourceContent"
                :disabled="selectionType != 'paste'"
            ></textarea>
        </span>
        <template v-slot:buttons>
            <b-button ref="btnClose" class="ui-button-default" id="btn-close" @click="$emit('dismiss')">
                {{ btnCloseTitle }}
            </b-button>
            <b-button
                ref="btnBuild"
                class="ui-button-default"
                id="btn-build"
                @click="_eventBuild"
                :disabled="!sourceContent"
                :variant="sourceContent ? 'primary' : ''"
            >
                {{ btnBuildTitle }}
            </b-button>
            <b-button
                ref="btnReset"
                class="ui-button-default"
                id="btn-reset"
                @click="_eventReset"
                :disabled="!enableReset"
            >
                {{ btnResetTitle }}
            </b-button>
        </template>
    </upload-wrapper>
</template>

<script>
import _l from "utils/localization";
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
    mixins: [UploadBoxMixin],
    components: { BLink, BButton, FontAwesomeIcon },
    data() {
        return {
            l: _l,
            datasets: [],
            ftpFiles: [],
            uris: [],
            topInfo: _l("Tabular source data to extract collection files and metadata from"),
            enableReset: false,
            enableBuild: false,
            dataType: "datasets",
            selectedDatasetId: null,
            selectedDatasetName: null,
            sourceContent: "",
            selectionType: "paste",
            btnBuildTitle: _l("Build"),
            btnResetTitle: _l("Reset"),
            btnCloseTitle: this.app.callback ? _l("Cancel") : _l("Close"),
        };
    },
    created() {
        this.initCollection();
        this.initAppProperties();
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
                    }/contents/${selectedDatasetId}/display`
                )
                .then((response) => {
                    this.sourceContent = response.data;
                })
                .catch((error) => console.log(error));
        },
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
            Galaxy.currHistoryPanel.buildCollection("rules", selection, true);
            this.app.hide();
        },
    },
};
</script>

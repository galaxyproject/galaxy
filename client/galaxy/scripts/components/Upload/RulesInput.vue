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
                        <option v-if="ftpUploadSite" value="ftp">{{ l("FTP Directory") }} </option></select2
                    >
                </div>
            </div>
            <div id="upload-rule-dataset-option" class="upload-rule-option" v-if="selectionType == 'dataset'">
                <div class="upload-rule-option-title">{{ l("Select dataset to load") }}</div>
                <div class="dataset-selector">
                    <select2
                        v-model="selectedDatasetId"
                        container-class="upload-footer-selection"
                        placeholder="Select Dataset"
                    >
                        <option></option>
                        <option v-for="dataset of datasets" :key="dataset.id" :value="dataset.id">
                            {{ dataset.hid }}: {{ dataset.name }}</option
                        >
                    </select2>
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
            <b-button ref="btnClose" class="ui-button-default" id="btn-close" @click="app.hide()">
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
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import UploadUtils from "mvc/upload/upload-utils";
import axios from "axios";
import { getAppRoot } from "onload/loadConfig";

Vue.use(BootstrapVue);

export default {
    mixins: [UploadBoxMixin],
    data() {
        return {
            l: _l,
            datasets: [],
            ftpFiles: [],
            datasetsSet: false,
            topInfo: _l("Tabular source data to extract collection files and metadata from"),
            enableReset: false,
            enableBuild: false,
            dataType: "datasets",
            selectedDatasetId: null,
            sourceContent: "",
            selectionType: "paste",
            btnBuildTitle: _l("Build"),
            btnResetTitle: _l("Reset"),
            btnCloseTitle: _l("Close"),
        };
    },
    created() {
        this.initCollection();
        this.initAppProperties();
    },
    watch: {
        selectionType: function (selectionType) {
            if (selectionType == "dataset" && !this.datasetsSet) {
                const Galaxy = getGalaxyInstance();
                const history = Galaxy && Galaxy.currHistoryPanel && Galaxy.currHistoryPanel.model;
                const historyContentModels = history.contents.models;
                for (const historyContentModel of historyContentModels) {
                    const attr = historyContentModel.attributes;
                    if (attr.history_content_type !== "dataset") {
                        continue;
                    }
                    this.datasets.push(attr);
                }
                this.datasetsSet = true;
            } else if (selectionType == "ftp") {
                UploadUtils.getRemoteFiles((ftp_files) => {
                    this.sourceContent = ftp_files.map((file) => file["path"]).join("\n");
                    this.ftpFiles = ftp_files;
                });
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

        _eventBuild: function () {
            this._buildSelection(this.sourceContent);
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
            }
            selection.dataType = this.dataType;
            Galaxy.currHistoryPanel.buildCollection("rules", selection, true);
            this.app.hide();
        },
    },
};
</script>

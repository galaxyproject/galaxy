import _ from "underscore";
import Backbone from "backbone";
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";
import _l from "utils/localization";
import Ui from "mvc/ui/ui-misc";
import Select from "mvc/ui/ui-select";
import UploadUtils from "mvc/upload/upload-utils";
import axios from "axios";

export default Backbone.View.extend({
    initialize: function(app) {
        this.app = app;
        this.options = app.options;
        this.ftpFiles = [];
        this.ftpUploadSite = app.currentFtp();
        this.setElement(this._template());
        this.btnBuild = new Ui.Button({
            id: "btn-build",
            title: _l("Build"),
            onclick: () => {
                this._eventBuild();
            }
        });
        this.btnBuild.$el.addClass("btn-primary");
        this.btnReset = new Ui.Button({
            id: "btn-reset",
            title: _l("Reset"),
            onclick: () => this._eventReset()
        });
        this.btnClose = new Ui.Button({
            id: "btn-close",
            title: _l("Close"),
            onclick: () => this.app.modal.hide()
        });
        _.each([this.btnReset, this.btnBuild, this.btnClose], button => {
            this.$(".upload-buttons").prepend(button.$el);
        });
        const dataTypeOptions = [{ id: "datasets", text: "Datasets" }, { id: "collections", text: "Collection(s)" }];
        this.dataType = "datasets";
        this.dataTypeView = new Select.View({
            css: "upload-footer-selection",
            container: this.$(".rule-data-type"),
            data: dataTypeOptions,
            value: this.dataType,
            onchange: value => {
                this.dataType = value;
                // this._renderSelectedType();
            }
        });

        const selectionTypeOptions = [
            { id: "paste", text: "Pasted Table" },
            { id: "dataset", text: "History Dataset" }
        ];
        if (this.ftpUploadSite) {
            selectionTypeOptions.push({ id: "ftp", text: "FTP Directory" });
        }
        this.selectionType = "paste";
        this.selectionTypeView = new Select.View({
            css: "upload-footer-selection",
            container: this.$(".rule-select-type"),
            data: selectionTypeOptions,
            value: this.selectionType,
            onchange: value => {
                this.selectionType = value;
                this._renderSelectedType();
            }
        });
        this.selectedDatasetId = null;

        this.$sourceContent = this.$(".upload-rule-source-content");
        this.$sourceContent.on("change keyup paste", () => {
            this._updateBuildState();
        });
        this._renderSelectedType();
    },

    _renderSelectedType: function() {
        const selectionType = this.selectionType;
        let Galaxy = getGalaxyInstance();
        if (selectionType == "dataset") {
            if (!this.datasetSelectorView) {
                this.selectedDatasetId = null;
                const history = Galaxy && Galaxy.currHistoryPanel && Galaxy.currHistoryPanel.model;
                const historyContentModels = history.contents.models;
                const options = [];
                for (let historyContentModel of historyContentModels) {
                    const attr = historyContentModel.attributes;
                    if (attr.history_content_type !== "dataset") {
                        continue;
                    }
                    options.push({ id: attr.id, text: `${attr.hid}: ${_.escape(attr.name)}` });
                }
                this.datasetSelectorView = new Select.View({
                    container: this.$(".dataset-selector"),
                    data: options,
                    placeholder: _l("Select a dataset"),
                    onchange: val => {
                        this._onDataset(val);
                    }
                });
            } else {
                this.datasetSelectorView.value(null);
            }
        } else if (selectionType == "ftp") {
            UploadUtils.getRemoteFiles(ftp_files => {
                this._setPreview(ftp_files.map(file => file["path"]).join("\n"));
                this.ftpFiles = ftp_files;
            });
        }
        this._updateScreen();
    },

    _onDataset: function(selectedDatasetId) {
        let Galaxy = getGalaxyInstance();
        this.selectedDatasetId = selectedDatasetId;
        if (!selectedDatasetId) {
            this._setPreview("");
            return;
        }
        axios
            .get(
                `${getAppRoot()}api/histories/${Galaxy.currHistoryPanel.model.id}/contents/${selectedDatasetId}/display`
            )
            .then(response => {
                this._setPreview(response.data);
            })
            .catch(error => console.log(error));
    },

    /** Remove all */
    _eventReset: function() {
        if (this.datasetSelectorView) {
            this.datasetSelectorView.value(null);
        }
        this.$sourceContent.val("");
        this._updateScreen();
    },

    _eventBuild: function() {
        const selection = this.$sourceContent.val();
        this._buildSelection(selection);
    },

    _buildSelection: function(content) {
        const selectionType = this.selectionType;
        const selection = {};
        let Galaxy = getGalaxyInstance();
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
        this.app.modal.hide();
    },

    _setPreview: function(content) {
        this.$sourceContent.val(content);
        this._updateScreen();
    },

    _updateScreen: function() {
        this._updateBuildState();
        const selectionType = this.selectionType;
        this.$("#upload-rule-dataset-option")[selectionType == "dataset" ? "show" : "hide"]();
        this.$sourceContent.attr("disabled", selectionType !== "paste");
    },

    _updateBuildState: function() {
        const selection = this.$sourceContent.val();
        this.btnBuild[selection ? "enable" : "disable"]();
        this.btnBuild.$el[selection ? "addClass" : "removeClass"]("btn-primary");
    },

    _template: function() {
        return `
            <div class="upload-view-default">
                <div class="upload-top">
                    <div class="upload-top-info">
                        Tabular source data to extract collection files and metadata from
                    </div>
                </div>
                <div class="upload-box" style="height: 335px;">
                    <span style="width: 25%; display: inline; height: 100%" class="float-left">
                        <div class="upload-rule-option">
                            <div class="upload-rule-option-title">${_l("Upload data as")}:</div>
                            <div class="rule-data-type" />
                        </div>
                        <div class="upload-rule-option">
                            <div class="upload-rule-option-title">${_l("Load tabular data from")}:</div>
                            <div class="rule-select-type" />
                        </div>
                        <div id="upload-rule-dataset-option" class="upload-rule-option">
                            <div class="upload-rule-option-title">${_l("Select dataset to load")}:</div>
                            <div class="dataset-selector" />
                        </div>
                    </span>
                    <span style="display: inline; float: right; width: 75%; height: 300px">
                    <textarea class="upload-rule-source-content form-control" style="height: 100%"></textarea>
                    </span>
                </div>
                <div class="clear" />
                <!--
                <div class="upload-footer">
                </div>
                -->
                <div class="upload-buttons"/>
                </div>
        `;
    }
});

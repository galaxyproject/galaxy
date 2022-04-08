<template>
    <upload-wrapper ref="wrapper" :top-info="topInfo" :highlight-box="highlightBox">
        <div class="upload-helper" v-show="showHelper"><i class="fa fa-files-o" />Drop files here</div>
        <table class="upload-table ui-table-striped" v-show="!showHelper" ref="uploadTable">
            <thead>
                <tr>
                    <th>Size</th>
                    <th>Status</th>
                    <th />
                </tr>
            </thead>
            <tbody />
        </table>
        <template v-slot:footer>
            <span class="upload-footer-title">Collection Type:</span>
            <select2
                container-class="upload-footer-collection-type"
                ref="footerCollectionType"
                v-model="collectionType"
                :enabled="!running">
                <option value="list">List</option>
                <option value="paired">Pair</option>
                <option value="list:paired">List of Pairs</option>
            </select2>
            <span class="upload-footer-title">File Type:</span>
            <select2
                container-class="upload-footer-extension"
                ref="footerExtension"
                v-model="extension"
                :enabled="!running">
                <option v-for="(ext, index) in extensions" :key="index" :value="ext.id">{{ ext.text }}</option>
            </select2>
            <span class="upload-footer-extension-info upload-icon-button fa fa-search" />
            <span class="upload-footer-title">Genome (set all):</span>
            <select2 container-class="upload-footer-genome" ref="footerGenome" v-model="genome" :enabled="!running">
                <option v-for="(listGenome, index) in listGenomes" :key="index" :value="listGenome.id">
                    {{ listGenome.text }}
                </option>
            </select2>
        </template>
        <template v-slot:buttons>
            <b-button
                ref="btnClose"
                class="ui-button-default"
                id="btn-close"
                :title="btnCloseTitle"
                @click="$emit('dismiss')">
                {{ btnCloseTitle | localize }}
            </b-button>
            <b-button
                ref="btnReset"
                class="ui-button-default"
                id="btn-reset"
                @click="_eventReset"
                :title="btnResetTitle"
                :disabled="!enableReset">
                {{ btnResetTitle }}
            </b-button>
            <b-button
                ref="btnStop"
                class="ui-button-default"
                id="btn-stop"
                @click="_eventStop"
                :title="btnStopTitle"
                :disabled="counterRunning == 0">
                {{ btnStopTitle }}
            </b-button>
            <b-button
                ref="btnBuild"
                class="ui-button-default"
                id="btn-build"
                @click="_eventBuild"
                :disabled="!enableBuild"
                :title="btnBuildTitle"
                :variant="enableBuild ? 'primary' : ''">
                {{ btnBuildTitle }}
            </b-button>
            <b-button
                ref="btnStart"
                class="ui-button-default"
                id="btn-start"
                @click="_eventStart"
                :title="btnStartTitle"
                :disabled="!enableStart"
                :variant="enableStart ? 'primary' : ''">
                {{ btnStartTitle }}
            </b-button>
            <b-button
                ref="btnCreate"
                class="ui-button-default"
                id="btn-new"
                @click="_eventCreate()"
                :title="btnCreateTitle"
                :disabled="!enableSources">
                <span class="fa fa-edit"></span>{{ btnCreateTitle }}
            </b-button>
            <b-button
                ref="btnFtp"
                class="ui-button-default"
                id="btn-ftp"
                @click="_eventRemoteFiles"
                :disabled="!enableSources"
                v-if="remoteFiles">
                <span class="fa fa-folder-open-o"></span>{{ btnFilesTitle }}
            </b-button>
            <b-button
                ref="btnLocal"
                class="ui-button-default"
                id="btn-local"
                :title="btnLocalTitle"
                @click="uploadSelect"
                :disabled="!enableSources">
                <span class="fa fa-laptop"></span>{{ btnLocalTitle }}
            </b-button>
        </template>
    </upload-wrapper>
</template>

<script>
import _l from "utils/localization";
import _ from "underscore";
import { getGalaxyInstance } from "app";
import UploadRow from "mvc/upload/collection/collection-row";
import UploadBoxMixin from "./UploadBoxMixin";
import { uploadModelsToPayload } from "./helpers";
import { BButton } from "bootstrap-vue";

export default {
    mixins: [UploadBoxMixin],
    components: { BButton },
    data() {
        return {
            uploadUrl: null,
            topInfo: "",
            showHelper: true,
            extension: this.app.defaultExtension,
            genome: this.app.defaultGenome,
            collectionType: "list",
            listExtensions: [],
            listGenomes: [],
            running: false,
            multiple: true, // needed for uploadbox stuff - always allow multiple uploads for collections
            counterAnnounce: 0,
            counterSuccess: 0,
            counterError: 0,
            counterRunning: 0,
            uploadSize: 0,
            uploadCompleted: 0,
            enableReset: false,
            enableStart: false,
            enableSources: false,
            enableBuild: false,
            highlightBox: false,
            rowUploadModel: UploadRow,
            btnLocalTitle: _l("Choose local files"),
            btnCreateTitle: _l("Paste/Fetch data"),
            btnFtpTitle: _l("Choose FTP files"),
            btnStartTitle: _l("Start"),
            btnBuildTitle: _l("Build"),
            btnStopTitle: _l("Pause"),
            btnResetTitle: _l("Reset"),
        };
    },
    created() {
        this.initCollection();
        this.initAppProperties();
    },
    mounted() {
        this.initExtensionInfo();
        this.initFtpPopover();
        // file upload
        this.initUploadbox({
            initUrl: (index) => {
                if (!this.uploadUrl) {
                    this.uploadUrl = this.getRequestUrl([this.collection.get(index)], this.history_id);
                }
                return this.uploadUrl;
            },
            announce: (index, file) => {
                this._eventAnnounce(index, file);
            },
            initialize: (index) => {
                return uploadModelsToPayload([this.collection.get(index)], this.history_id);
            },
            progress: (index, percentage) => {
                this._eventProgress(index, percentage);
            },
            success: (index, message) => {
                this._eventSuccess(index, message);
            },
            warning: (index, message) => {
                this._eventWarning(index, message);
            },
            error: (index, message) => {
                this._eventError(index, message);
            },
            complete: () => {
                this._eventComplete();
            },
            ondragover: () => {
                this.highlightBox = true;
            },
            ondragleave: () => {
                this.highlightBox = false;
            },
            chunkSize: this.app.chunkUploadSize,
        });
        this.collection.on("remove", (model) => {
            this._eventRemove(model);
        });
        this._updateStateForCounters();
    },
    computed: {
        extensions() {
            const result = _.filter(this.listExtensions, (ext) => !ext.composite_files);
            return result;
        },
        appModel() {
            return this.app.model;
        },
    },
    watch: {
        extension: function (value) {
            this.updateExtension(value);
        },
        genome: function (value) {
            this.updateGenome(value);
        },
    },
    methods: {
        _newUploadModelProps: function (index, file) {
            return {
                id: index,
                file_name: file.name,
                file_size: file.size,
                file_mode: file.mode || "local",
                file_path: file.path,
                file_data: file,
                file_uri: file.uri,
                extension: this.extension,
                genome: this.genome,
            };
        },

        /** Success */
        _eventSuccess: function (index, incoming) {
            var it = this.collection.get(index);
            console.debug("Incoming upload response.", incoming);
            // accounts for differences in the response format between upload methods
            const outputs = incoming.outputs || incoming.data.outputs || {};
            it.set({ percentage: 100, status: "success", outputs });
            this._updateStateForSuccess(it);
            const Galaxy = getGalaxyInstance();
            Galaxy.currHistoryPanel.refreshContents();
        },

        _eventBuild: function () {
            const Galaxy = getGalaxyInstance();
            const models = {};
            this.collection.models.forEach((model) => {
                const outputs = model.get("outputs");
                if (outputs) {
                    Object.entries(outputs).forEach((output) => {
                        const outputDetails = output[1];
                        models[outputDetails.id] = outputDetails;
                    });
                } else {
                    console.debug("Warning, upload response does not contain outputs.", model);
                }
            });
            const selection = new Galaxy.currHistoryPanel.collection.constructor(Object.values(models));
            selection.historyId = Galaxy.currHistoryPanel.model.id;
            Galaxy.currHistoryPanel.buildCollection(this.collectionType, selection, true);
            this.counterRunning = 0;
            this._updateStateForCounters();
            this._eventReset();
            this.$emit("dismiss");
        },

        /** Remove all */
        _eventReset: function () {
            if (this.counterRunning == 0) {
                this.collection.reset();
                this.counterAnnounce = 0;
                this.counterSuccess = 0;
                this.counterError = 0;
                this.counterRunning = 0;
                this.uploadbox.reset();
                this.extension = this.app.defaultExtension;
                this.genome = this.app.defaultGenome;
                this.appModel.set("percentage", 0);
                this._updateStateForCounters();
            }
        },
    },
};
</script>

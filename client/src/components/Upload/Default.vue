<template>
    <upload-wrapper ref="wrapper" :top-info="topInfo" :highlight-box="highlightBox">
        <div class="upload-helper" v-show="showHelper"><i class="fa fa-files-o" />Drop files here</div>
        <table class="upload-table ui-table-striped" v-show="!showHelper" ref="uploadTable">
            <thead>
                <tr>
                    <th>Name</th>
                    <th>Size</th>
                    <th>Type</th>
                    <th>Genome</th>
                    <th>Settings</th>
                    <th>Status</th>
                    <th />
                </tr>
            </thead>
            <tbody />
        </table>
        <template v-slot:footer>
            <span class="upload-footer-title">Type (set all):</span>
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
                {{ btnCloseTitle }}
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
                ref="btnStart"
                class="ui-button-default"
                id="btn-start"
                @click="_eventStart"
                :disabled="!enableStart"
                :title="btnStartTitle"
                :variant="enableStart ? 'primary' : ''">
                {{ btnStartTitle }}
            </b-button>
            <b-button
                ref="btnCreate"
                class="ui-button-default"
                id="btn-new"
                @click="_eventCreate(true)"
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
import UploadRow from "mvc/upload/default/default-row";
import UploadBoxMixin from "./UploadBoxMixin";
import { uploadModelsToPayload } from "./helpers";
import { BButton } from "bootstrap-vue";

export default {
    mixins: [UploadBoxMixin],
    components: { BButton },
    props: {
        multiple: {
            type: Boolean,
            default: true,
        },
    },
    data() {
        return {
            uploadUrl: null,
            topInfo: "",
            highlightBox: false,
            showHelper: true,
            extension: this.app.defaultExtension,
            genome: this.app.defaultGenome,
            listExtensions: [],
            listGenomes: [],
            running: false,
            rowUploadModel: UploadRow,
            counterAnnounce: 0,
            counterSuccess: 0,
            counterError: 0,
            counterRunning: 0,
            uploadSize: 0,
            uploadCompleted: 0,
            enableReset: false,
            enableStart: false,
            enableSources: false,
            btnLocalTitle: _l("Choose local files"),
            btnCreateTitle: _l("Paste/Fetch data"),
            btnStartTitle: _l("Start"),
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
            multiple: this.multiple,
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
            error: (index, message) => {
                this._eventError(index, message);
            },
            warning: (index, message) => {
                this._eventWarning(index, message);
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
                file_uri: file.uri,
                file_data: file,
            };
        },

        /** Success */
        _eventSuccess: function (index, incoming) {
            var it = this.collection.get(index);
            it.set({ ...incoming["outputs"], percentage: 100, status: "success" });
            this._updateStateForSuccess(it);
        },

        /** Remove all */
        _eventReset: function () {
            if (this.counterRunning === 0) {
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

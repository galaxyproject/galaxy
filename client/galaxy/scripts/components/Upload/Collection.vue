<template>
    <upload-wrapper ref="wrapper" :topInfo="topInfo" :hightlightBox="hightlightBox">
        <div class="upload-helper" v-show="showHelper"><i class="fa fa-files-o" />Drop files here</div>
        <table class="upload-table ui-table-striped" v-show="!showHelper" ref="uploadTable">
            <thead>
                <tr>
                    <th>Name</th>
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
                containerClass="upload-footer-collection-type"
                ref="footerCollectionType"
                v-model="collectionType"
                :enabled="!running"
            >
                <option value="list">List</option>
                <option value="paired">Pair</option>
                <option value="list:paired">List of Pairs</option>
            </select2>
            <span class="upload-footer-title">File Type:</span>
            <select2
                containerClass="upload-footer-extension"
                ref="footerExtension"
                v-model="extension"
                :enabled="!running"
            >
                <option v-for="(extension, index) in extensions" v-bind:key="index" :value="extension.id">{{
                    extension.text
                }}</option>
            </select2>
            <span class="upload-footer-extension-info upload-icon-button fa fa-search" />
            <span class="upload-footer-title">Genome (set all):</span>
            <select2 containerClass="upload-footer-genome" ref="footerGenome" v-model="genome" :enabled="!running">
                <option v-for="(genome, index) in listGenomes" v-bind:key="index" :value="genome.id">{{
                    genome.text
                }}</option>
            </select2>
        </template>
        <template v-slot:buttons>
            <b-button ref="btnClose" class="ui-button-default" id="btn-close" @click="app.hide()">
                {{ btnCloseTitle }}
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
            <b-button
                ref="btnStop"
                class="ui-button-default"
                id="btn-stop"
                @click="_eventStop"
                :disabled="counterRunning == 0"
            >
                {{ btnStopTitle }}
            </b-button>
            <b-button
                ref="btnBuild"
                class="ui-button-default"
                id="btn-build"
                @click="_eventBuild"
                :disabled="!enableBuild"
                :variant="enableBuild ? 'primary' : ''"
            >
                {{ btnBuildTitle }}
            </b-button>
            <b-button
                ref="btnStart"
                class="ui-button-default"
                id="btn-start"
                @click="_eventStart"
                :disabled="!enableStart"
                :variant="enableStart ? 'primary' : ''"
            >
                {{ btnStartTitle }}
            </b-button>
            <b-button
                ref="btnCreate"
                class="ui-button-default"
                id="btn-new"
                @click="_eventCreate"
                :disabled="!enableSources"
            >
                <span class="fa fa-edit"></span>{{ btnCreateTitle }}
            </b-button>
            <b-button
                ref="btnFtp"
                class="ui-button-default"
                id="btn-ftp"
                @click="_eventFtp"
                :disabled="!enableSources"
                v-if="ftpUploadSite"
            >
                <span class="fa fa-folder-open-o"></span>{{ btnFtpTitle }}
            </b-button>
            <b-button
                ref="btnLocal"
                class="ui-button-default"
                id="btn-local"
                :title="btnLocalTitle"
                @click="uploadSelect"
                :disabled="!enableSources"
            >
                <span class="fa fa-laptop"></span>{{ btnLocalTitle }}
            </b-button>
        </template>
    </upload-wrapper>
</template>

<script>
import _l from "utils/localization";
import _ from "underscore";
import { getGalaxyInstance } from "app";
import UploadModel from "mvc/upload/upload-model";
import UploadRow from "mvc/upload/collection/collection-row";
import UploadFtp from "mvc/upload/upload-ftp";
import UploadBoxMixin from "./UploadBoxMixin";
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";

Vue.use(BootstrapVue);

export default {
    mixins: [UploadBoxMixin],
    data() {
        return {
            topInfo: "",
            showHelper: true,
            extension: this.app.defaultExtension,
            genome: this.app.defaultGenome,
            collectionType: "list",
            listExtensions: [],
            listGenomes: [],
            running: false,
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
            hightlightBox: false,
            btnLocalTitle: _l("Choose local files"),
            btnCreateTitle: _l("Paste/Fetch data"),
            btnFtpTitle: _l("Choose FTP files"),
            btnStartTitle: _l("Start"),
            btnBuildTitle: _l("Build"),
            btnStopTitle: _l("Pause"),
            btnResetTitle: _l("Reset"),
            btnCloseTitle: _l("Close")
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
            url: this.app.uploadPath,
            announce: (index, file) => {
                this._eventAnnounce(index, file);
            },
            initialize: index => {
                return this.app.toData([this.collection.get(index)], this.history_id);
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
            complete: () => {
                this._eventComplete();
            },
            ondragover: () => {
                this.hightlightBox = true;
            },
            ondragleave: () => {
                this.hightlightBox = false;
            }
        });
        this.collection.on("remove", model => {
            this._eventRemove(model);
        });
        this._updateScreen();
    },
    computed: {
        extensions() {
            const result = _.filter(this.listExtensions, ext => !ext.composite_files);
            return result;
        },
        appModel() {
            return this.app.model;
        }
    },
    watch: {
        extension: function(value) {
            this.updateExtension(value);
        },
        genome: function(value) {
            this.updateGenome(value);
        }
    },
    methods: {
        uploadSelect: function() {
            this.uploadbox.select();
        },
        /** A new file has been dropped/selected through the uploadbox plugin */
        _eventAnnounce: function(index, file) {
            this.counterAnnounce++;
            var new_model = new UploadModel.Model({
                id: index,
                file_name: file.name,
                file_size: file.size,
                file_mode: file.mode || "local",
                file_path: file.path,
                file_data: file,
                extension: this.extension,
                genome: this.genome
            });
            this.collection.add(new_model);
            var upload_row = new UploadRow(this, { model: new_model });
            this.$uploadTable()
                .find("tbody:first")
                .append(upload_row.$el);
            this._updateScreen();
            // render does width and offset dynamically so we need to wait a tick
            // for Vue to show the table (or maybe row)
            this.$nextTick(() => {
                upload_row.render();
            });
        },

        /** Progress */
        _eventProgress: function(index, percentage) {
            var it = this.collection.get(index);
            it.set("percentage", percentage);
            this.appModel.set("percentage", this._uploadPercentage(percentage, it.get("file_size")));
        },

        /** Success */
        _eventSuccess: function(index, message) {
            // var hdaId = message["outputs"][0]["id"];
            var hids = _.pluck(message["outputs"], "hid");
            var it = this.collection.get(index);
            it.set({ percentage: 100, status: "success", hids: hids });
            this.appModel.set("percentage", this._uploadPercentage(100, it.get("file_size")));
            this.uploadCompleted += it.get("file_size") * 100;
            this.counterAnnounce--;
            this.counterSuccess++;
            this._updateScreen();
            const Galaxy = getGalaxyInstance();
            Galaxy.currHistoryPanel.refreshContents();
        },

        /** Error */
        _eventError: function(index, message) {
            var it = this.collection.get(index);
            it.set({ percentage: 100, status: "error", info: message });
            this.appModel.set({
                percentage: this._uploadPercentage(100, it.get("file_size")),
                status: "danger"
            });
            this.uploadCompleted += it.get("file_size") * 100;
            this.counterAnnounce--;
            this.counterError++;
            this._updateScreen();
        },

        /** Queue is done */
        _eventComplete: function() {
            this.collection.each(model => {
                model.get("status") == "queued" && model.set("status", "init");
            });
            this.counterRunning = 0;
            this._updateScreen();
        },

        _eventBuild: function() {
            const Galaxy = getGalaxyInstance();
            var allHids = [];
            _.forEach(this.collection.models, upload => {
                allHids.push.apply(allHids, upload.get("hids"));
            });
            var models = _.map(allHids, hid => Galaxy.currHistoryPanel.collection.getByHid(hid));
            var selection = new Galaxy.currHistoryPanel.collection.constructor(models);
            // I'm building the selection wrong because I need to set this historyId directly.
            selection.historyId = Galaxy.currHistoryPanel.collection.historyId;
            Galaxy.currHistoryPanel.buildCollection(this.collectionType, selection, true);
            this.counterRunning = 0;
            this._updateScreen();
            this._eventReset();
            this.app.hide();
        },

        /** Remove model from upload list */
        _eventRemove: function(model) {
            var status = model.get("status");
            if (status == "success") {
                this.counterSuccess--;
            } else if (status == "error") {
                this.counterError--;
            } else {
                this.counterAnnounce--;
            }
            this.uploadbox.remove(model.id);
            this._updateScreen();
        },

        //
        // events triggered by this view
        //

        /** Show/hide ftp popup */
        _eventFtp: function() {
            this.ftp.show(
                new UploadFtp({
                    collection: this.collection,
                    ftp_upload_site: this.ftpUploadSite,
                    onadd: ftp_file => {
                        return this.uploadbox.add([
                            {
                                mode: "ftp",
                                name: ftp_file.path,
                                size: ftp_file.size,
                                path: ftp_file.path
                            }
                        ]);
                    },
                    onremove: function(model_index) {
                        this.collection.remove(model_index);
                    }
                }).$el
            );
        },

        /** Create a new file */
        _eventCreate: function() {
            this.uploadbox.add([{ name: "New File", size: 0, mode: "new" }]);
        },

        /** Start upload process */
        _eventStart: function() {
            if (this.counterAnnounce == 0 || this.counterRunning > 0) {
                return;
            }
            this.uploadSize = 0;
            this.uploadCompleted = 0;
            this.collection.each(model => {
                if (model.get("status") == "init") {
                    model.set("status", "queued");
                    this.uploadSize += model.get("file_size");
                }
            });
            this.appModel.set({ percentage: 0, status: "success" });
            this.counterRunning = this.counterAnnounce;
            this.history_id = this.app.currentHistory();
            this.uploadbox.start();
            this._updateScreen();
        },

        /** Pause upload process */
        _eventStop: function() {
            if (this.counterRunning > 0) {
                this.appModel.set("status", "info");
                this.topInfo = "Queue will pause after completing the current file...";
                this.uploadbox.stop();
            }
        },

        /** Remove all */
        _eventReset: function() {
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
                this._updateScreen();
            }
        },
        /** Set screen */
        _updateScreen: function() {
            var message = "";
            if (this.counterAnnounce == 0) {
                if (this.uploadbox.compatible()) {
                    message = "&nbsp;";
                } else {
                    message =
                        "Browser does not support Drag & Drop. Try Firefox 4+, Chrome 7+, IE 10+, Opera 12+ or Safari 6+.";
                }
            } else {
                if (this.counterRunning == 0) {
                    message = `You added ${this.counterAnnounce} file(s) to the queue. Add more files or click 'Start' to proceed.`;
                } else {
                    message = `Please wait...${this.counterAnnounce} out of ${this.counterRunning} remaining.`;
                }
            }
            this.topInfo = message;
            this.enableReset =
                this.counterRunning == 0 && this.counterAnnounce + this.counterSuccess + this.counterError > 0;
            this.enableStart = this.counterRunning == 0 && this.counterAnnounce > 0;
            this.enableBuild =
                this.counterRunning == 0 &&
                this.counterAnnounce == 0 &&
                this.counterSuccess > 0 &&
                this.counterError == 0;
            this.enableSources = this.counterRunning == 0;
            var show_table = this.counterAnnounce + this.counterSuccess + this.counterError > 0;
            this.showHelper = !show_table;
        },

        /** Calculate percentage of all queued uploads */
        _uploadPercentage: function(percentage, size) {
            return (this.uploadCompleted + percentage * size) / this.uploadSize;
        }
    }
};
</script>

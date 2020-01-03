<template>
    <upload-wrapper ref="wrapper" :topInfo="topInfo">
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
import $ from "jquery";
import { getGalaxyInstance } from "app";
import UploadModel from "mvc/upload/upload-model";
import UploadRow from "mvc/upload/default/default-row";
import UploadBoxMixin from "./UploadBoxMixin";
import LazyLimited from "mvc/lazy/lazy-limited";
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
            btnFtpTitle: _l("Choose FTP files"),
            btnStartTitle: _l("Start"),
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
            warning: (index, message) => {
                this._eventWarning(index, message);
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
        const $uploadBox = this.$uploadBox();
        // Lazy load helper
        this.loader = new LazyLimited({
            $container: $uploadBox,
            collection: this.collection,
            new_content: model => {
                return this.registerNewModel(model);
            }
        });
        this.collection.on("remove", model => {
            this._eventRemove(model);
        });
        this._updateStateForCounters();
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
        /** A new file has been dropped/selected through the uploadbox plugin */
        _eventAnnounce: function(index, file) {
            this.counterAnnounce++;
            var newModel = new UploadModel.Model({
                id: index,
                file_name: file.name,
                file_size: file.size,
                file_mode: file.mode || "local",
                file_path: file.path,
                file_data: file
            });
            this.collection.add(newModel);
            this._updateStateForCounters();
        },

        /** Success */
        _eventSuccess: function(index, message) {
            var it = this.collection.get(index);
            it.set({ percentage: 100, status: "success" });
            this._updateStateForSuccess(it);
        },

        /** Start upload process */
        _eventStart: function() {
            if (this.counterAnnounce !== 0 && this.counterRunning === 0) {
                // prepare upload process
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
                // package ftp files separately, and remove them from queue
                this._uploadFtp();

                // queue remaining files
                const Galaxy = getGalaxyInstance();
                this.uploadbox.start({
                    id: Galaxy.user.id,
                    chunk_upload_size: this.app.chunkUploadSize
                });
                this._updateStateForCounters();
            }
        },

        /** Remove all */
        _eventReset: function() {
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

        /** Package and upload ftp files in a single request */
        _uploadFtp: function() {
            var self = this;
            var list = [];
            this.collection.each(model => {
                if (model.get("status") == "queued" && model.get("file_mode") == "ftp") {
                    self.uploadbox.remove(model.id);
                    list.push(model);
                }
            });
            if (list.length > 0) {
                $.uploadpost({
                    data: this.app.toData(list),
                    url: this.app.uploadPath,
                    success: function(message) {
                        _.each(list, model => {
                            self._eventSuccess(model.id);
                        });
                    },
                    error: function(message) {
                        _.each(list, model => {
                            self._eventError(model.id, message);
                        });
                    }
                });
            }
        }
    }
};
</script>

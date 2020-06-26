<template>
    <b-modal
        v-model="modalShow"
        :static="modalStatic"
        header-class="no-separator"
        modal-class="ui-modal"
        dialog-class="upload-dialog"
        body-class="upload-dialog-body"
        no-enforce-focus
        hide-footer
    >
        <template v-slot:modal-header>
            <h4 class="title" tabindex="0">{{ title }}</h4>
        </template>
        <b-tabs v-if="historyAvailable">
            <b-tab title="Regular" id="regular" button-id="tab-title-link-regular">
                <default :app="this" :lazy-load-max="50" />
            </b-tab>
            <b-tab title="Composite" id="composite" button-id="tab-title-link-composite">
                <composite :app="this" />
            </b-tab>
            <b-tab title="Collection" id="collection" button-id="tab-title-link-collection">
                <collection :app="this" />
            </b-tab>
            <b-tab title="Rule-based" id="rule-based" button-id="tab-title-link-rule-based">
                <rules-input :app="this" />
            </b-tab>
        </b-tabs>
        <div v-else>
            Loading required information from Galaxy server.
        </div>
    </b-modal>
</template>

<script>
import Backbone from "backbone";
import $ from "jquery";
import _l from "utils/localization";
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import { getGalaxyInstance } from "app";
import UploadUtils from "mvc/upload/upload-utils";
import Composite from "./Composite";
import Collection from "./Collection";
import Default from "./Default";
import RulesInput from "./RulesInput";

Vue.use(BootstrapVue);

export default {
    components: {
        Collection,
        Composite,
        Default,
        RulesInput,
    },
    props: {
        modalStatic: {
            type: Boolean,
            default: true,
        },
        chunkUploadSize: {
            type: Number,
            required: true,
        },
        uploadPath: {
            type: String,
            required: true,
        },
        modalShow: {
            type: Boolean,
            default: false,
        },
        ftpUploadSite: {
            type: String,
            default: "n/a",
        },
        defaultGenome: {
            type: String,
            default: UploadUtils.DEFAULT_GENOME,
        },
        defaultExtension: {
            type: String,
            default: UploadUtils.DEFAULT_EXTENSION,
        },
        datatypesDisableAuto: {
            type: Boolean,
            default: false,
        },
        auto: {
            type: Object,
            default: function () {
                return UploadUtils.AUTO_EXTENSION;
            },
        },
    },
    data: function () {
        return {
            title: _l("Download from web or upload from disk"),
            historyAvailable: false,
            currentUser: null,
            listGenomes: [],
            listExtensions: [],
        };
    },
    created: function () {
        this.model = new Backbone.Model({
            label: "Load Data",
            percentage: 0,
            status: "",
            onunload: function () {},
            onclick: function () {},
        });
        $(window).on("beforeunload", () => this.model.get("onunload")());

        // load extensions
        UploadUtils.getUploadDatatypes(
            (listExtensions) => {
                this.listExtensions = listExtensions;
            },
            this.datatypesDisableSuto,
            this.auto
        );

        // load genomes
        UploadUtils.getUploadGenomes((listGenomes) => {
            this.listGenomes = listGenomes;
        }, this.defaultGenome);

        this.initStateWhenHistoryReady();
    },
    methods: {
        show() {
            this.modalShow = true;
            this.$nextTick(this.tryMountingTabs);
        },
        hide() {
            this.modalShow = false;
        },
        initStateWhenHistoryReady() {
            const Galaxy = getGalaxyInstance();
            if (!Galaxy.currHistoryPanel || !Galaxy.currHistoryPanel.model) {
                window.setTimeout(() => {
                    this.initStateWhenHistoryReady();
                }, 500);
                return;
            }
            this.historyAvailable = true;
            this.currentUser = Galaxy.user.id;
        },
        currentFtp: function () {
            return this.currentUser && this.ftpUploadSite;
        },
        /** Refresh user and current history */
        currentHistory: function () {
            const Galaxy = getGalaxyInstance();
            return this.currentUser && Galaxy.currHistoryPanel.model.get("id");
        },
        /**
         * Package API data from array of models
         * @param{Array} items - Upload items/rows filtered from a collection
         */
        toData: function (items, history_id) {
            // create dictionary for data submission
            var data = {
                payload: {
                    tool_id: "upload1",
                    history_id: history_id || this.currentHistory(),
                    inputs: {},
                },
                files: [],
                error_message: null,
            };
            // add upload tools input data
            if (items && items.length > 0) {
                var inputs = {
                    file_count: items.length,
                    dbkey: items[0].get("genome", "?"),
                    // sometimes extension set to "" in automated testing after first upload of
                    // a session. https://github.com/galaxyproject/galaxy/issues/5169
                    file_type: items[0].get("extension") || "auto",
                };
                for (var index in items) {
                    var it = items[index];
                    it.set("status", "running");
                    if (it.get("file_size") > 0) {
                        var prefix = `files_${index}|`;
                        inputs[`${prefix}type`] = "upload_dataset";
                        if (it.get("file_name") != "New File") {
                            inputs[`${prefix}NAME`] = it.get("file_name");
                        }
                        inputs[`${prefix}space_to_tab`] = (it.get("space_to_tab") && "Yes") || null;
                        inputs[`${prefix}to_posix_lines`] = (it.get("to_posix_lines") && "Yes") || null;
                        inputs[`${prefix}dbkey`] = it.get("genome", null);
                        inputs[`${prefix}file_type`] = it.get("extension", null);
                        switch (it.get("file_mode")) {
                            case "new":
                                inputs[`${prefix}url_paste`] = it.get("url_paste");
                                break;
                            case "ftp":
                                inputs[`${prefix}ftp_files`] = it.get("file_path");
                                break;
                            case "local":
                                data.files.push({
                                    name: `${prefix}file_data`,
                                    file: it.get("file_data"),
                                });
                        }
                    } else if (it.get("optional")) {
                        continue;
                    } else {
                        data.error_message = "Upload content incomplete.";
                        it.set("status", "error");
                        it.set("info", data.error_message);
                        break;
                    }
                }
                data.payload.inputs = JSON.stringify(inputs);
            }
            return data;
        },
    },
};
</script>

<style>
.upload-dialog {
    width: 900px;
}
.upload-dialog-body {
    height: 500px;
    overflow: hidden;
}
</style>

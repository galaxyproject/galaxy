<template>
    <b-modal
        v-model="modalShow"
        :static="modalStatic"
        header-class="no-separator"
        modal-class="ui-modal"
        dialog-class="upload-dialog"
        body-class="upload-dialog-body"
        ref="modal"
        no-enforce-focus
        hide-footer
        :id="id"
    >
        <template v-slot:modal-header>
            <h4 class="title" tabindex="0">{{ title }}</h4>
        </template>
        <b-tabs v-if="ready">
            <b-tab title="Regular" id="regular" button-id="tab-title-link-regular" v-if="showRegular">
                <default :app="this" :lazy-load-max="50" :multiple="multiple" :selectable="callback != null" />
            </b-tab>
            <b-tab title="Composite" id="composite" button-id="tab-title-link-composite" v-if="showComposite">
                <composite :app="this" />
            </b-tab>
            <b-tab title="Collection" id="collection" button-id="tab-title-link-collection" v-if="showCollection">
                <collection :app="this" />
            </b-tab>
            <b-tab title="Rule-based" id="rule-based" button-id="tab-title-link-rule-based" v-if="showRules">
                <rules-input :app="this" />
            </b-tab>
        </b-tabs>
        <div v-else>
            <loading-span message="Loading required information from Galaxy server." />
        </div>
    </b-modal>
</template>

<script>
import _l from "utils/localization";
import Backbone from "backbone";
import UploadUtils from "mvc/upload/upload-utils";
import { getDatatypesMapper } from "components/Datatypes";
import Composite from "./Composite";
import Collection from "./Collection";
import Default from "./Default";
import RulesInput from "./RulesInput";
import LoadingSpan from "components/LoadingSpan";
import { mapState } from "vuex";
import { BModal, BTabs, BTab } from "bootstrap-vue";
import { isBetaHistoryOpen } from "components/History/adapters/betaToggle";

const UploadModal = {
    components: {
        Collection,
        Composite,
        Default,
        RulesInput,
        LoadingSpan,
        BModal,
        BTabs,
        BTab,
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
        fileSourcesConfigured: {
            type: Boolean,
            default: false,
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
        formats: {
            type: Array,
            default: null,
        },
        multiple: {
            // Restrict the forms to a single dataset upload if false
            type: Boolean,
            default: true,
        },
        callback: {
            // Return uploads when done if supplied.
            type: Function,
            default: null,
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
            id: "",
            title: _l("Download from web or upload from disk"),
            listGenomes: [],
            listExtensions: [],
            genomesSet: false,
            extensionsSet: false,
            datatypesMapper: null,
            datatypesMapperReady: true,
        };
    },
    created() {
        this.model = new Backbone.Model({
            label: "Load Data",
            percentage: 0,
            status: "",
            onunload: function () {},
            onclick: function () {},
        });

        // load extensions
        UploadUtils.getUploadDatatypes(
            (listExtensions) => {
                this.extensionsSet = true;
                this.listExtensions = listExtensions;
            },
            this.datatypesDisableAuto,
            this.auto
        );

        // load genomes
        UploadUtils.getUploadGenomes((listGenomes) => {
            this.genomesSet = true;
            this.listGenomes = listGenomes;
        }, this.defaultGenome);

        if (this.formats !== null) {
            this.datatypesMapperReady = false;
            getDatatypesMapper().then((datatypesMapper) => {
                this.datatypesMapper = datatypesMapper;
                this.datatypesMapperReady = true;
            });
        } else {
            this.datatypesMapperReady = true;
        }
    },
    beforeDestroy() {
        const modelUnload = this.model.get("onunload");
        modelUnload();
    },
    computed: {
        ...mapState("user", {
            currentUserId: (state) => state.currentUser.id,
        }),

        // go straight to "state" instead of getter because the getter would filter out a current id
        // that wasn't in the list
        ...mapState("betaHistory", {
            currentHistoryId: (state) => state.currentHistoryId,
        }),

        historyAvailable() {
            return Boolean(this.currentHistoryId);
        },

        ready() {
            return this.genomesSet && this.extensionsSet && this.historyAvailable && this.datatypesMapperReady;
        },

        unrestricted() {
            return this.formats === null && this.multiple;
        },

        effectiveExtensions() {
            if (this.formats === null || !this.datatypesMapperReady) {
                return this.listExtensions;
            }
            const effectiveExtensions = [];
            this.listExtensions.forEach((extension) => {
                if (extension && extension.id == "auto") {
                    effectiveExtensions.push(extension);
                } else if (this.datatypesMapper.isSubTypeOfAny(extension.id, this.formats)) {
                    effectiveExtensions.push(extension);
                }
            });
            return effectiveExtensions;
        },
        formatRestricted() {
            return this.formats !== null;
        },
        showComposite() {
            if (!this.formatRestricted) {
                return true;
            }
            return this.effectiveExtensions.some((extension) => !!extension.composite_files);
        },
        showRegular() {
            if (!this.formatRestricted) {
                return true;
            }
            return this.effectiveExtensions.some((extension) => !extension.composite_files);
        },
        showCollection() {
            if (this.unrestricted) {
                return true;
            }
            return false;
        },
        showRules() {
            if (this.unrestricted) {
                return true;
            }
            return this.multiple;
        },
    },
    mounted() {
        this.id = String(this._uid);
    },
    methods: {
        show() {
            this.modalShow = true;
            this.$nextTick(this.tryMountingTabs);
        },
        hide() {
            this.modalShow = false;
        },
        cancel() {
            this.hide();
            this.$nextTick(() => {
                this.$bvModal.hide(this.id, "cancel");
                this.$destroy();
            });
        },
        dismiss() {
            // hide or cancel based on whether this is a singleton
            if (this.callback) {
                this.cancel();
            } else {
                this.hide();
            }
        },
        currentFtp: function () {
            return this.currentUserId && this.ftpUploadSite;
        },
        toData: function (items, history_id) {
            var data = {
                fetchRequest: null,
                uploadRequest: null,
            };
            if (items && items.length > 0) {
                var split = this.preprocess(items);
                if (split.urls.length > 0) {
                    // TODO multiple fetches?
                    data.fetchRequest = this.toFetchData(split.urls, history_id);
                }
                if (split.files.length > 0) {
                    data.uploadRequest = this.toFileUploadData(split.files, history_id);
                }
            }
            return data;
        },
        preprocess: function (items) {
            var data = {
                urls: [],
                files: [],
            };
            for (var index in items) {
                var it = items[index];
                console.log("it ", it);
                if (it.get("file_mode") != "new" || !it.get("url_paste").startsWith("http")) {
                    data.files.push(it);
                } else {
                    data.urls.push(it);
                }
            }
            console.log("data ", data);
            return data;
        },
        /**
         * Package API data from array of models
         * @param{Array} items - Upload items/rows filtered from a collection
         */
        toFileUploadData: function (items, history_id) {
            // create dictionary for data submission
            var data = {
                payload: {
                    tool_id: "upload1",
                    history_id: history_id || this.currentHistoryId,
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
                        let uri;
                        let how;
                        switch (it.get("file_mode")) {
                            case "new":
                                inputs[`${prefix}url_paste`] = it.get("url_paste");
                                break;
                            case "ftp":
                                uri = it.get("file_path");
                                how = "ftp_files";
                                if (uri.indexOf("://") >= 0) {
                                    how = "url_paste";
                                }
                                inputs[`${prefix}${how}`] = uri;
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
            console.log("inUploadData:", data);
            return data;
        },
        toFetchData: function (items, history_id) {
            
            // TODO create the request body - see RuleCollectionBuilder._datasetFor
            var data = {
                history_id: history_id,
                targets: [
                    {
                        destination: { type: "hdas" },
                        elements: [],
                        name: "",
                    },
                ],
                auto_decompress: true,
            };

            // TODO iterate through items - maybe there's only one?
            const urls = items[0].get("url_paste").split("\n");
            for (var index in urls) {
                var element = {
                    url: urls[index],
                    src: "url",
                    dbkey: "?",
                    ext: "auto",
                };
                data.targets[0].elements.push(element);
            }
            console.log("***inFetchData:****", data);
            return data;
        },
    },
};

// Beta history patch
if (isBetaHistoryOpen()) {
    UploadModal.computed.currentHistoryId = function () {
        return this.$store.getters["betaHistory/currentHistoryId"];
    };
}

export default UploadModal;
</script>

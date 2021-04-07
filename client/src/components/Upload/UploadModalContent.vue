<template>
    <b-tabs v-if="ready">
        <b-tab title="Regular" id="regular" button-id="tab-title-link-regular" v-if="showRegular">
            <default
                :app="this"
                :lazy-load-max="50"
                :multiple="multiple"
                :has-callback="hasCallback"
                :selectable="selectable"
                v-on="$listeners"
            />
        </b-tab>
        <b-tab title="Composite" id="composite" button-id="tab-title-link-composite" v-if="showComposite">
            <composite :app="this" :has-callback="hasCallback" :selectable="selectable" v-on="$listeners" />
        </b-tab>
        <b-tab title="Collection" id="collection" button-id="tab-title-link-collection" v-if="showCollection">
            <collection :app="this" :has-callback="hasCallback" :selectable="selectable" v-on="$listeners" />
        </b-tab>
        <b-tab title="Rule-based" id="rule-based" button-id="tab-title-link-rule-based" v-if="showRules">
            <rules-input :app="this" :has-callback="hasCallback" :selectable="selectable" v-on="$listeners" />
        </b-tab>
    </b-tabs>
    <div v-else>
        <loading-span message="Loading required information from Galaxy server." />
    </div>
</template>

<script>
import Backbone from "backbone";
import UploadUtils from "mvc/upload/upload-utils";
import { getDatatypesMapper } from "components/Datatypes";
import Composite from "./Composite";
import Collection from "./Collection";
import Default from "./Default";
import RulesInput from "./RulesInput";
import LoadingSpan from "components/LoadingSpan";
import { BTabs, BTab } from "bootstrap-vue";
import { commonProps } from "./helpers";

export default {
    components: {
        Collection,
        Composite,
        Default,
        RulesInput,
        LoadingSpan,
        BTabs,
        BTab,
    },
    props: {
        currentHistoryId: { type: String, required: true },
        currentUserId: { type: String, default: "" },
        ...commonProps,
    },
    data: function () {
        return {
            listGenomes: [],
            listExtensions: [],
            genomesSet: false,
            extensionsSet: false,
            datatypesMapper: null,
            datatypesMapperReady: true,
            URI_PREFIXES: ["http", "https", "ftp", "file", "gxfiles", "gximport", "gxuserimport", "gxftp"],
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

        this.model.on("change", (model) => {
            const { changed } = model;
            for (const [field, val] of Object.entries(changed)) {
                this.eventHub.$emit(`upload:${field}`, val);
            }
        });

        // load extensions
        // TODO: provider...
        UploadUtils.getUploadDatatypes(this.datatypesDisableAuto, this.auto)
            .then((listExtensions) => {
                this.extensionsSet = true;
                this.listExtensions = listExtensions;
            })
            .catch((err) => {
                console.log("Error in UploadModalContent, unable to load datatypes", err);
            });

        // load genomes
        // TODO: provider...
        UploadUtils.getUploadGenomes(this.defaultGenome)
            .then((listGenomes) => {
                this.genomesSet = true;
                this.listGenomes = listGenomes;
            })
            .catch((err) => {
                console.log("Error in uploadModalContent, unable to load genomes", err);
            });

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
        currentFtp: function () {
            return this.currentUserId && this.ftpUploadSite;
        },
        toData: function (items, history_id) {
            const data = {
                fetchRequest: null,
                uploadRequest: null,
            };
            if (items && items.length > 0) {
                const split = this.preprocess(items);
                if (split.urls.length > 0) {
                    data.fetchRequest = this.toFetchData(split.urls, history_id);
                } else {
                    data.uploadRequest = this.toFileUploadData(split.files, history_id);
                }
            }
            return data;
        },
        preprocess: function (items) {
            const data = {
                urls: [],
                files: [],
            };
            for (var index in items) {
                var it = items[index];
                if (it.get("file_mode") != "new" || !this.itemIsURL(it)) {
                    data.files.push(it);
                } else {
                    data.urls.push(it);
                }
            }
            return data;
        },
        itemIsURL: function (item) {
            return this.URI_PREFIXES.some((prefix) => item.get("url_paste").startsWith(prefix));
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
            return data;
        },
        toFetchData: function (items, history_id) {
            var data = {
                history_id: history_id,
                space_to_tab: items[0].get("space_to_tab"),
                to_posix_lines: items[0].get("to_posix_lines"),
                targets: [
                    {
                        destination: { type: "hdas" },
                        elements: [],
                        name: "",
                    },
                ],
                auto_decompress: true,
            };

            // Composite does not use the fetch API, so we can just
            // index into the first element of items
            const urls = items[0].get("url_paste").split("\n");
            for (var index in urls) {
                var url = urls[index].trim();
                if (url != "") {
                    var element = {
                        url: urls[index].trim(),
                        src: "url",
                        dbkey: items[0].get("genome", "?"),
                        ext: items[0].get("extension", "auto"),
                    };
                    data.targets[0].elements.push(element);
                }
            }
            return data;
        },
    },
};
</script>

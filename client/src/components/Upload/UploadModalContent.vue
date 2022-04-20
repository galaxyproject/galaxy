<template>
    <b-tabs v-if="ready">
        <b-tab v-if="showRegular" id="regular" title="Regular" button-id="tab-title-link-regular">
            <default
                :app="this"
                :lazy-load-max="50"
                :multiple="multiple"
                :has-callback="hasCallback"
                :selectable="selectable"
                v-on="$listeners" />
        </b-tab>
        <b-tab v-if="showComposite" id="composite" title="Composite" button-id="tab-title-link-composite">
            <composite :app="this" :has-callback="hasCallback" :selectable="selectable" v-on="$listeners" />
        </b-tab>
        <b-tab v-if="showCollection" id="collection" title="Collection" button-id="tab-title-link-collection">
            <collection :app="this" :has-callback="hasCallback" :selectable="selectable" v-on="$listeners" />
        </b-tab>
        <b-tab v-if="showRules" id="rule-based" title="Rule-based" button-id="tab-title-link-rule-based">
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
import { uploadModelsToPayload } from "./helpers";
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
        };
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
    mounted() {
        this.id = String(this._uid);
    },
    methods: {
        currentFtp: function () {
            return this.currentUserId && this.ftpUploadSite;
        },
        /**
         * Package API data from array of backbone models
         * @param{Array} items - Upload items/rows filtered from a collection
         */
        toData: function (items, history_id, composite = false) {
            return uploadModelsToPayload(items, history_id, composite);
        },
    },
};
</script>

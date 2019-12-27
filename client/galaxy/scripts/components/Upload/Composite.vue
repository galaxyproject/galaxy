<template>
    <upload-wrapper wrapperClass="upload-view-composite">
        <table class="upload-table ui-table-striped" style="display: none;" ref="uploadTable">
            <thead>
                <tr>
                    <th />
                    <th />
                    <th>Description</th>
                    <th>Name</th>
                    <th>Size</th>
                    <th>Settings</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody />
        </table>
        <template v-slot:footer>
            <span class="upload-footer-title">Composite Type:</span>
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
            <span class="upload-footer-extension-info upload-icon-button fa fa-search" ref="footerExtensionInfo" />
            <span class="upload-footer-title">Genome/Build:</span>
            <select2 containerClass="upload-footer-genome" ref="footerGenome" v-model="genome" :enabled="!running">
                <option v-for="(genome, index) in listGenomes" v-bind:key="index" :value="genome.id">{{
                    genome.text
                }}</option>
            </select2>
        </template>
        <template v-slot:buttons>
            <div ref="uploadButtons" />
        </template>
    </upload-wrapper>
</template>

<script>
import _l from "utils/localization";
import _ from "underscore";
import $ from "jquery";
import { getGalaxyInstance } from "app";
import UploadRow from "mvc/upload/composite/composite-row";
import Ui from "mvc/ui/ui-misc";
import UploadBoxMixin from "./UploadBoxMixin";

export default {
    mixins: [UploadBoxMixin],
    data() {
        return {
            extension: "_select_",
            genome: this.app.defaultGenome,
            listExtensions: [],
            listGenomes: [],
            running: false
        };
    },
    created() {
        this.initCollection();
        this.initAppProperties();

        // TODO: to template in Vue
        this.btnReset = new Ui.Button({
            id: "btn-reset",
            title: _l("Reset"),
            onclick: () => {
                this._eventReset();
            }
        });
        this.btnStart = new Ui.Button({
            title: _l("Start"),
            onclick: () => {
                this._eventStart();
            }
        });
        this.btnClose = new Ui.Button({
            title: _l("Close"),
            onclick: () => {
                this.app.hide();
            }
        });
    },
    computed: {
        extensions() {
            const result = _.filter(this.listExtensions, ext => ext.composite_files);
            result.unshift({ id: "_select_", text: "Select" });
            return result;
        }
    },
    mounted() {
        // init buttons
        _.each([this.btnReset, this.btnStart, this.btnClose], button => {
            $(this.$refs.uploadButtons).prepend(button.$el);
        });

        this.initExtensionInfo();
        // listener for collection triggers on change in composite datatype and extension selection
        this.collection.on("add", model => {
            this._eventAnnounce(model);
        });
        this.collection.on("change add", () => {
            this.renderNonReactiveComponents();
        });
        this.renderNonReactiveComponents();
    },
    methods: {
        $uploadTable() {
            return $(this.$refs.uploadTable);
        },
        renderNonReactiveComponents: function() {
            var model = this.collection.first();
            if (model && model.get("status") == "running") {
                this.running = true;
            } else {
                this.running = false;
            }
            if (
                this.collection.where({ status: "ready" }).length + this.collection.where({ optional: true }).length ==
                    this.collection.length &&
                this.collection.length > 0
            ) {
                this.btnStart.enable();
                this.btnStart.$el.addClass("btn-primary");
            } else {
                this.btnStart.disable();
                this.btnStart.$el.removeClass("btn-primary");
            }
            this.$uploadTable()[this.collection.length > 0 ? "show" : "hide"]();
        },

        //
        // upload events / process pipeline
        //

        /** Builds the basic ui with placeholder rows for each composite data type file */
        _eventAnnounce: function(model) {
            var upload_row = new UploadRow(this, { model: model });
            this.$uploadTable()
                .find("tbody:first")
                .append(upload_row.$el);
            this.$uploadTable()[this.collection.length > 0 ? "show" : "hide"]();
            upload_row.render();
        },

        /** Start upload process */
        _eventStart: function() {
            this.collection.each(model => {
                model.set({
                    genome: this.genome,
                    extension: this.extension
                });
            });
            $.uploadpost({
                url: this.app.uploadPath,
                data: this.app.toData(this.collection.filter()),
                success: message => {
                    this._eventSuccess(message);
                },
                error: message => {
                    this._eventError(message);
                },
                progress: percentage => {
                    this._eventProgress(percentage);
                }
            });
        },

        /** Remove all */
        _eventReset: function() {
            if (this.collection.where({ status: "running" }).length == 0) {
                this.collection.reset();
                this.extension = this.app.defaultExtension;
                this.genome = this.app.defaultGenome;
                this.renderNonReactiveComponents();
            }
        },

        /** Refresh progress state */
        _eventProgress: function(percentage) {
            this.collection.each(it => {
                it.set("percentage", percentage);
            });
        },

        /** Refresh success state */
        _eventSuccess: function(message) {
            const Galaxy = getGalaxyInstance();
            this.collection.each(it => {
                it.set("status", "success");
            });
            Galaxy.currHistoryPanel.refreshContents();
        },

        /** Refresh error state */
        _eventError: function(message) {
            this.collection.each(it => {
                it.set({ status: "error", info: message });
            });
        }
    },
    watch: {
        extension: function(value) {
            this.collection.reset();
            var details = _.findWhere(this.listExtensions, {
                id: value
            });
            if (details && details.composite_files) {
                _.each(details.composite_files, item => {
                    this.collection.add({
                        id: this.collection.size(),
                        file_desc: item.description || item.name,
                        optional: item.optional
                    });
                });
            }
        }
    }
};
</script>

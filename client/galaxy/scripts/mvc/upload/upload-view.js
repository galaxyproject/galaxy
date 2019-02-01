/** Upload app contains the upload progress button and upload modal, compiles model data for API request **/
import _l from "utils/localization";
import Backbone from "backbone";
import { getGalaxyInstance } from "app";
import Utils from "utils/utils";
import Modal from "mvc/ui/ui-modal";
import Tabs from "mvc/ui/ui-tabs";
import UploadUtils from "mvc/upload/upload-utils";
import UploadButton from "mvc/upload/upload-button";
import UploadViewDefault from "mvc/upload/default/default-view";
import UploadViewComposite from "mvc/upload/composite/composite-view";
import UploadViewCollection from "mvc/upload/collection/collection-view";
import UploadViewRuleBased from "mvc/upload/collection/rules-input-view";

export default Backbone.View.extend({
    options: {
        ftp_upload_site: "n/a",
        default_genome: UploadUtils.DEFAULT_GENOME,
        default_extension: UploadUtils.DEFAULT_EXTENSION,
        height: 500,
        width: 900,
        auto: UploadUtils.AUTO_EXTENSION
    },

    // contains all available dataset extensions/types
    list_extensions: [],

    // contains all available genomes
    list_genomes: [],

    initialize: function(options) {
        this.options = Utils.merge(options, this.options);

        // create view for upload/progress button
        this.ui_button = new UploadButton.View({
            onclick: e => {
                e.preventDefault();
                this.show();
            },
            onunload: () => {
                var percentage = this.ui_button.model.get("percentage", 0);
                if (percentage > 0 && percentage < 100) {
                    return "Several uploads are queued.";
                }
            }
        });

        // set element to button view
        this.setElement(this.ui_button.$el);

        // load extensions
        UploadUtils.getUploadDatatypes(
            list_extensions => {
                this.list_extensions = list_extensions;
            },
            this.options.datatypes_disable_auto,
            this.options.auto
        );

        // load genomes
        UploadUtils.getUploadGenomes(list_genomes => {
            this.list_genomes = list_genomes;
        }, this.default_genome);
    },

    /** Show/hide upload dialog */
    show: function() {
        let Galaxy = getGalaxyInstance();
        var self = this;
        if (!Galaxy.currHistoryPanel || !Galaxy.currHistoryPanel.model) {
            window.setTimeout(() => {
                self.show();
            }, 500);
            return;
        }
        this.current_user = Galaxy.user.id;
        if (!this.modal) {
            this.tabs = new Tabs.View();
            this.default_view = new UploadViewDefault(this);
            this.tabs.add({
                id: "regular",
                title: _l("Regular"),
                $el: this.default_view.$el
            });
            this.composite_view = new UploadViewComposite(this);
            this.tabs.add({
                id: "composite",
                title: _l("Composite"),
                $el: this.composite_view.$el
            });
            this.collection_view = new UploadViewCollection(this);
            this.tabs.add({
                id: "collection",
                title: _l("Collection"),
                $el: this.collection_view.$el
            });
            this.rule_based_view = new UploadViewRuleBased(this);
            this.tabs.add({
                id: "rule-based",
                title: _l("Rule-based"),
                $el: this.rule_based_view.$el
            });
            this.modal = new Modal.View({
                title: _l("Download from web or upload from disk"),
                body: this.tabs.$el,
                height: this.options.height,
                width: this.options.width,
                closing_events: true,
                title_separator: false
            });
        }
        this.modal.show();
    },

    /** Refresh user and current history */
    currentHistory: function() {
        let Galaxy = getGalaxyInstance();
        return this.current_user && Galaxy.currHistoryPanel.model.get("id");
    },

    /** Get ftp configuration */
    currentFtp: function() {
        return this.current_user && this.options.ftp_upload_site;
    },

    /**
     * Package API data from array of models
     * @param{Array} items - Upload items/rows filtered from a collection
     */
    toData: function(items, history_id) {
        // create dictionary for data submission
        var data = {
            payload: {
                tool_id: "upload1",
                history_id: history_id || this.currentHistory(),
                inputs: {}
            },
            files: [],
            error_message: null
        };
        // add upload tools input data
        if (items && items.length > 0) {
            var inputs = {
                file_count: items.length,
                dbkey: items[0].get("genome", "?"),
                // sometimes extension set to "" in automated testing after first upload of
                // a session. https://github.com/galaxyproject/galaxy/issues/5169
                file_type: items[0].get("extension") || "auto"
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
                                file: it.get("file_data")
                            });
                    }
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
    }
});

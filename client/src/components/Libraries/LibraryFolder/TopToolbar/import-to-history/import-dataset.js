import { getGalaxyInstance } from "app";
import { Toast } from "ui/toast";
import _l from "utils/localization";
import mod_library_model from "mvc/library/library-model";
import _ from "underscore";
import Backbone from "backbone";
import $ from "jquery";
import { getAppRoot } from "onload/loadConfig";
import { updateProgress } from "../delete-selected";

var ImportDatasetModal = Backbone.View.extend({
    options: null,

    initialize: function (options) {
        this.options = options;
        this.options.chain_call_control = {
            total_number: 0,
            failed_number: 0,
        };
        this.importToHistoryModal();
    },
    findCheckedItems: function () {
        return this.options.selected;
    },
    importToHistoryModal: function () {
        const Galaxy = getGalaxyInstance();
        var $checkedValues = this.findCheckedItems();
        var template = this.templateImportIntoHistoryModal();
        if ($checkedValues.length === 0) {
            Toast.info("You must select some datasets first.");
        } else {
            var promise = this.fetchUserHistories();
            promise
                .done(() => {
                    this.modal = Galaxy.modal;
                    this.modal.show({
                        closing_events: true,
                        title: _l("Import into History"),
                        body: template({
                            histories: this.histories.models,
                        }),
                        buttons: {
                            Import: () => {
                                this.importAllIntoHistory();
                            },
                            Close: () => {
                                Galaxy.modal.hide();
                            },
                        },
                    });
                })
                .fail((model, response) => {
                    if (typeof response.responseJSON !== "undefined") {
                        Toast.error(response.responseJSON.err_msg);
                    } else {
                        Toast.error("An error occurred.");
                    }
                });
        }
    },

    /**
     * This function returns a promise
     */
    fetchUserHistories: function () {
        this.histories = new mod_library_model.GalaxyHistories();
        return this.histories.fetch();
    },

    importAllIntoHistory: function () {
        this.modal.disableButton("Import");
        var new_history_name = this.modal.$("input[name=history_name]").val();
        if (new_history_name !== "") {
            this.createNewHistory(new_history_name)
                .done((new_history) => {
                    this.processImportToHistory(new_history.id, new_history.name);
                })
                .fail((xhr, status, error) => {
                    Toast.error("An error occurred.");
                })
                .always(() => {
                    this.modal.disableButton("Import");
                });
        } else {
            var history_id = $("select[name=import_to_history] option:selected").val();
            var history_name = $("select[name=import_to_history] option:selected").text();
            this.processImportToHistory(history_id, history_name);
            this.modal.disableButton("Import");
        }
    },

    /**
     * This function returns a promise
     */
    createNewHistory: function (new_history_name) {
        return $.post(`${getAppRoot()}api/histories`, { name: new_history_name });
    },

    processImportToHistory: function (history_id, history_name) {
        var checked_items = this.findCheckedItems();
        var items_to_import = [];
        // prepare the dataset objects to be imported
        for (let i = checked_items.dataset_ids.length - 1; i >= 0; i--) {
            const library_dataset_id = checked_items.dataset_ids[i];
            const historyItem = new mod_library_model.HistoryItem();
            historyItem.url = `${historyItem.urlRoot + history_id}/contents`;
            historyItem.content = library_dataset_id;
            historyItem.source = "library";
            items_to_import.push(historyItem);
        }

        checked_items.folder_ids = checked_items.folder_ids ? checked_items.folder_ids : [];
        // prepare the folder objects to be imported
        for (let i = checked_items.folder_ids.length - 1; i >= 0; i--) {
            const library_folder_id = checked_items.folder_ids[i];
            const historyItem = new mod_library_model.HistoryItem();
            historyItem.url = `${historyItem.urlRoot + history_id}/contents`;
            historyItem.content = library_folder_id;
            historyItem.source = "library_folder";
            items_to_import.push(historyItem);
        }
        this.initChainCallControlToHistory({
            length: items_to_import.length,
            history_name: history_name,
        });
        // set the used history as current so user will see the last one
        // that he imported into in the history panel on the 'analysis' page
        $.getJSON(`${getAppRoot()}history/set_as_current?id=${history_id}`);
        this.chainCallImportingIntoHistory(items_to_import, history_name);
    },

    initChainCallControlToHistory: function (options) {
        var template;
        template = this.templateImportIntoHistoryProgressBar();
        this.modal.$el.find(".modal-body").html(template({ history_name: options.history_name }));

        // var progress_bar_tmpl = this.templateAddingDatasetsProgressBar();
        // this.modal.$el.find( '.modal-body' ).html( progress_bar_tmpl( { folder_name : this.options.folder_name } ) );
        this.progress = 0;
        this.progressStep = 100 / options.length;
        this.options.chain_call_control.total_number = options.length;
        this.options.chain_call_control.failed_number = 0;
    },
    /**
     * Take array of empty history items and make request for each of them
     * to create it on server. Update progress in between calls.
     * @param  {array} history_item_set array of empty history items
     * @param  {str} history_name     name of the history to import to
     */
    chainCallImportingIntoHistory: function (history_item_set, history_name) {
        const Galaxy = getGalaxyInstance();
        var popped_item = history_item_set.pop();
        if (typeof popped_item == "undefined") {
            if (this.options.chain_call_control.failed_number === 0) {
                Toast.success("Selected datasets imported into history. Click this to start analyzing it.", "", {
                    onclick: () => {
                        window.location = getAppRoot();
                    },
                });
            } else if (this.options.chain_call_control.failed_number === this.options.chain_call_control.total_number) {
                Toast.error("There was an error and no datasets were imported into history.");
            } else if (this.options.chain_call_control.failed_number < this.options.chain_call_control.total_number) {
                Toast.warning(
                    "Some of the datasets could not be imported into history. Click this to see what was imported.",
                    "",
                    {
                        onclick: () => {
                            window.location = getAppRoot();
                        },
                    }
                );
            }
            Galaxy.modal.hide();
            return true;
        }
        var promise = $.when(
            popped_item.save({
                content: popped_item.content,
                source: popped_item.source,
            })
        );

        promise
            .done(() => {
                updateProgress();
                this.chainCallImportingIntoHistory(history_item_set, history_name);
            })
            .fail(() => {
                this.options.chain_call_control.failed_number += 1;
                updateProgress();
                this.chainCallImportingIntoHistory(history_item_set, history_name);
            });
    },

    templateImportIntoHistoryProgressBar: function () {
        return _.template(
            `<div class="import_text">
                Importing selected items to history <b><%= _.escape(history_name) %></b>
            </div>
            <div class="progress">
                <div class="progress-bar progress-bar-import" role="progressbar" aria-valuenow="0" aria-valuemin="0"
                    aria-valuemax="100" style="width: 00%;">
                    <span class="completion_span">0% Complete</span>
                </div>
            </div>`
        );
    },
    templateDeletingItemsProgressBar: function () {
        return _.template(
            `<div class="import_text">
            </div>
            <div class="progress">
                <div class="progress-bar progress-bar-import" role="progressbar" aria-valuenow="0" aria-valuemin="0"
                    aria-valuemax="100" style="width: 00%;">
                    <span class="completion_span">0% Complete</span>
                </div>
            </div>`
        );
    },
    templateImportIntoHistoryModal: function () {
        return _.template(
            `<div>
                <div class="library-modal-item">
                    Select history:
                    <select name="import_to_history" style="width:50%; margin-bottom: 1em; " autofocus>
                        <% _.each(histories, function(history) { %>
                            <option value="<%= _.escape(history.get("id")) %>">
                                <%= _.escape(history.get("name")) %>
                            </option>
                        <% }); %>
                    </select>
                </div>
                <div class="library-modal-item">
                    or create new:
                    <input type="text" name="history_name" value=""
                        placeholder="name of the new history" style="width:50%;" />
                </div>
            </div>`
        );
    },
});

export default {
    ImportDatasetModal: ImportDatasetModal,
};

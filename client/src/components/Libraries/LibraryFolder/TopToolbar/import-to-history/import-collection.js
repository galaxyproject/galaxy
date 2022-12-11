import { getGalaxyInstance } from "app";
import { getAppRoot } from "onload/loadConfig";
import { Toast } from "composables/toast";
import mod_library_model from "../library-model";
import _ from "underscore";
import Backbone from "backbone";
import axios from "axios";

var ImportCollectionModal = Backbone.View.extend({
    options: null,

    initialize: function (options) {
        this.options = options;
        this.options.chain_call_control = {
            total_number: 0,
            failed_number: 0,
        };
        this.showCollectionSelect();
    },

    findCheckedItems: function () {
        return this.options.selected;
    },
    // TODO find a way to import this part from another component.... or just vuefy this module!
    fetchUserHistories: function () {
        this.histories = new mod_library_model.GalaxyHistories();
        return this.histories.fetch();
    },
    async createNewHistory(new_history_name) {
        const { data } = await axios.post(`${getAppRoot()}api/histories`, { name: new_history_name });
        getGalaxyInstance().currHistoryPanel.switchToHistory(data.id);
        return data;
    },
    showCollectionSelect: function (e) {
        const Galaxy = getGalaxyInstance();
        var checked_items = this.findCheckedItems();
        if (checked_items.length === 0) {
            Toast.info("You must select some datasets first.");
        } else {
            var template = this.templateCollectionSelectModal();

            var promise = this.fetchUserHistories();
            promise
                .done(() => {
                    this.modal = Galaxy.modal;
                    this.modal.show({
                        closing_events: true,
                        title: "Create History Collection from Datasets",
                        body: template({
                            selected_datasets: checked_items.dataset_ids.length,
                            histories: this.histories.models,
                        }),
                        buttons: {
                            Continue: () => {
                                this.showCollectionBuilder(checked_items.dataset_ids);
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
     * Note: The collection creation process expects ldda_ids as ids
     * in the collection_elements array but we operate on ld_ids in libraries.
     * The code below overwrites the id with ldda_id for this reason.
     */
    showCollectionBuilder: function (checked_items) {
        const collection_elements = [];
        for (let i = checked_items.length - 1; i >= 0; i--) {
            const collection_item = {};
            const dataset = checked_items[i];
            collection_item.id = dataset.ldda_id;
            collection_item.name = dataset.name;
            collection_item.deleted = dataset.deleted;
            collection_item.state = dataset.state;
            collection_item.src = "ldda";
            collection_elements.push(collection_item);
        }
        const new_history_name = this.modal.$("input[name=history_name]").val();
        if (new_history_name !== "") {
            this.createNewHistory(new_history_name)
                .then((new_history) => {
                    Toast.success("History created");
                    this.collectionImport(collection_elements, new_history.id);
                })
                .catch((error) => {
                    console.error(error);
                    Toast.error("An error occurred.");
                });
        } else {
            this.select_collection_history = this.modal.$el.find("#library-collection-history-select");
            const selected_history_id = this.select_collection_history.val();
            this.collectionImport(collection_elements, selected_history_id);
        }
    },
    collectionImport: function (collectionElements, historyId) {
        const collectionType = this.modal.$el.find("#library-collection-type-select").val();
        let selection = null;
        if (collectionType == "rules") {
            selection = collectionElements;
            selection.selectionType = "library_datasets";
        } else {
            selection = {
                models: collectionElements,
            };
        }
        const Galaxy = getGalaxyInstance();
        Galaxy.currHistoryPanel.buildCollection(collectionType, selection, historyId);
    },
    templateCollectionSelectModal: function () {
        return _.template(
            `<div> <!-- elements selection -->
                <!-- type selection -->
                <div class="library-modal-item">
                    <h4>Collection type</h4>
                    <div class="form-group">
                        <select id="library-collection-type-select" name="library-collection-type-select" class="form-control">
                            <option value="list">List</option>
                            <option value="paired">Paired</option>
                            <option value="list:paired">List of Pairs</option>
                            <option value="rules">From Rules</option>
                        </select>
                    </div>
                    <h5>Which type to choose?</h5>
                    <dl class="row">
                        <dt class="col-sm-3">List</dt>
                        <dd class="col-sm-9">Generic collection which groups any number of datasets into a set; similar to file system folder.</dd>

                        <dt class="col-sm-3">Paired</dt>
                        <dd class="col-sm-9">Simple collection containing exactly two sequence datasets; one reverse and the other forward.</dd>

                        <dt class="col-sm-3">List of Pairs</dt>
                        <dd class="col-sm-9">Advanced collection containing any number of Pairs; imagine as Pair-type collections inside of a List-type collection.</dd>

                        <dt class="col-sm-3">From Rules</dt>
                        <dd class="col-sm-9">Use Galaxy's rule builder to describe collections. This is more of an advanced feature that allows building any number of collections or any type.</dd>
                    </dl>
                </div>
                <!-- history selection/creation -->
                <div class="library-modal-item">
                    <h4>Select history</h4>
                    <div class="form-group">
                        <select id="library-collection-history-select" name="library-collection-history-select" class="form-control">
                            <% _.each(histories, function(history) { %> <!-- history select box -->
                                <option value="<%= _.escape(history.get("id")) %>">
                                    <%= _.escape(history.get("name")) %>
                                </option>
                            <% }); %>
                        </select>
                        <label>or create new:</label>
                        <input class="form-control" type="text" name="history_name" value="" placeholder="name of the new history" />
                    </div>
                </div>
            </div>`
        );
    },
});

export default {
    ImportCollectionModal: ImportCollectionModal,
};

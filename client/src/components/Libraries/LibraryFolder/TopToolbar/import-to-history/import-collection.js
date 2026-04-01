import axios from "axios";
import { escape } from "lodash";

import { buildCollectionFromRules } from "@/components/Collections/common/buildCollectionModal";
import { Toast } from "@/composables/toast";
import { getAppRoot } from "@/onload/loadConfig";
import { useHistoryStore } from "@/stores/historyStore";
import Modal from "@/utils/modal";

var modal = new Modal();

class ImportCollectionModal {
    constructor(options) {
        this.options = options;
        this.options.chain_call_control = {
            total_number: 0,
            failed_number: 0,
        };
        this.histories = [];
        this.showCollectionSelect();
    }

    findCheckedItems() {
        return this.options.selected;
    }

    async fetchUserHistories() {
        const { data } = await axios.get(`${getAppRoot()}api/histories`);
        this.histories = data;
    }

    async createNewHistory(new_history_name) {
        const { data } = await axios.post(`${getAppRoot()}api/histories`, { name: new_history_name });
        const { setCurrentHistory } = useHistoryStore();
        await setCurrentHistory(data.id);
        return data;
    }

    async showCollectionSelect() {
        var checked_items = this.findCheckedItems();
        if (checked_items.length === 0) {
            Toast.info("You must select some datasets first.");
        } else {
            try {
                await this.fetchUserHistories();
                modal.show({
                    closing_events: true,
                    title: "Create History Collection from Datasets",
                    body: this.templateCollectionSelectModal({
                        selected_datasets: checked_items.dataset_ids.length,
                        histories: this.histories,
                    }),
                    buttons: {
                        Continue: () => {
                            modal.hide();
                            this.showCollectionBuilder(checked_items.dataset_ids);
                        },
                        Close: () => {
                            modal.hide();
                        },
                    },
                });
            } catch (error) {
                const response = error.response;
                if (response?.data?.err_msg) {
                    Toast.error(response.data.err_msg);
                } else {
                    Toast.error("An error occurred.");
                }
            }
        }
    }

    showCollectionBuilder(checked_items) {
        const collection_elements = [];
        for (let i = checked_items.length - 1; i >= 0; i--) {
            const dataset = checked_items[i];
            collection_elements.push({
                id: dataset.ldda_id,
                name: dataset.name,
                deleted: dataset.deleted,
                state: dataset.state,
                src: "ldda",
            });
        }
        const new_history_name = modal.el.querySelector('input[name="history_name"]').value;
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
            this.select_collection_history = modal.el.querySelector("#library-collection-history-select");
            const selected_history_id = this.select_collection_history.value;
            this.collectionImport(collection_elements, selected_history_id);
        }
    }

    collectionImport(collectionElements, historyId) {
        const collectionType = modal.el.querySelector("#library-collection-type-select").value;
        const selection = { models: collectionElements };
        if (collectionType === "rules") {
            buildCollectionFromRules(selection, historyId);
        } else if (this.options.onCollectionImport) {
            this.options.onCollectionImport(collectionType, selection, historyId);
        }
    }

    templateCollectionSelectModal({ histories }) {
        const historyOptions = histories
            .map((history) => `<option value="${escape(history.id)}">${escape(history.name)}</option>`)
            .join("\n");
        return `<div>
                <div class="library-modal-item">
                    <h4>Select history</h4>
                    <div class="form-group">
                        <select id="library-collection-history-select" name="library-collection-history-select" class="form-control">
                            ${historyOptions}
                        </select>
                        <label>or create new:</label>
                        <input class="form-control" type="text" name="history_name" value="" placeholder="name of the new history" />
                    </div>
                </div>
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
            </div>`;
    }
}

export default {
    ImportCollectionModal: ImportCollectionModal,
};

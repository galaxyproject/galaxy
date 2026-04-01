import axios from "axios";
import { escape } from "lodash";

import { Toast } from "@/composables/toast";
import { getAppRoot } from "@/onload/loadConfig";
import _l from "@/utils/localization";
import Modal from "@/utils/modal";

import { updateProgressBar } from "../delete-selected";

var modal = new Modal();

class ImportDatasetModal {
    constructor(options) {
        this.options = options;
        this.options.chain_call_control = {
            total_number: 0,
            failed_number: 0,
        };
        this.histories = [];
        this.progress = 0;
        this.progressStep = 0;
        this.importToHistoryModal();
    }

    findCheckedItems() {
        return this.options.selected;
    }

    async importToHistoryModal() {
        var checkedValues = this.findCheckedItems();
        if (checkedValues.length === 0) {
            Toast.info("You must select some datasets first.");
            return;
        }
        try {
            await this.fetchUserHistories();
            modal.show({
                closing_events: true,
                title: _l("Import into History"),
                body: this.templateImportIntoHistoryModal({ histories: this.histories }),
                buttons: {
                    Import: () => {
                        this.importAllIntoHistory();
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

    async fetchUserHistories() {
        const { data } = await axios.get(`${getAppRoot()}api/histories`);
        this.histories = data;
    }

    async importAllIntoHistory() {
        modal.disableButton("Import");
        var new_history_name = modal.el.querySelector('input[name="history_name"]').value;
        if (new_history_name !== "") {
            try {
                const { data: new_history } = await axios.post(`${getAppRoot()}api/histories`, {
                    name: new_history_name,
                });
                this.processImportToHistory(new_history.id, new_history.name);
            } catch {
                Toast.error("An error occurred.");
            } finally {
                modal.enableButton("Import");
            }
        } else {
            const selectEl = modal.el.querySelector("select[name=import_to_history]");
            const selectedOption = selectEl.options[selectEl.selectedIndex];
            var history_id = selectedOption.value;
            var history_name = selectedOption.textContent;
            this.processImportToHistory(history_id, history_name);
            modal.enableButton("Import");
        }
    }

    processImportToHistory(history_id, history_name) {
        var checked_items = this.findCheckedItems();
        var items_to_import = [];

        for (let i = checked_items.dataset_ids.length - 1; i >= 0; i--) {
            items_to_import.push({
                content: checked_items.dataset_ids[i],
                source: "library",
            });
        }

        checked_items.folder_ids = checked_items.folder_ids ? checked_items.folder_ids : [];
        for (let i = checked_items.folder_ids.length - 1; i >= 0; i--) {
            items_to_import.push({
                content: checked_items.folder_ids[i],
                source: "library_folder",
            });
        }

        this.initChainCallControlToHistory({
            length: items_to_import.length,
            history_name: history_name,
        });

        axios.get(`${getAppRoot()}history/set_as_current?id=${history_id}`).catch(() => {});
        this.chainCallImportingIntoHistory(items_to_import, history_name, history_id);
    }

    initChainCallControlToHistory(options) {
        modal.$body.innerHTML = this.templateImportIntoHistoryProgressBar({ history_name: options.history_name });
        this.progress = 0;
        this.progressStep = 100 / options.length;
        this.options.chain_call_control.total_number = options.length;
        this.options.chain_call_control.failed_number = 0;
    }

    async chainCallImportingIntoHistory(items, history_name, history_id) {
        const contentsUrl = `${getAppRoot()}api/histories/${history_id}/contents`;
        while (items.length > 0) {
            var item = items.pop();
            try {
                await axios.post(contentsUrl, {
                    content: item.content,
                    source: item.source,
                });
            } catch {
                this.options.chain_call_control.failed_number += 1;
            }
            this.progress += this.progressStep;
            updateProgressBar(this.progress);
        }

        if (this.options.chain_call_control.failed_number === 0) {
            Toast.success(
                "Click here to start analyzing it.",
                "Selected datasets imported into history",
                `${getAppRoot()}histories/view?id=${history_id}`,
            );
        } else if (this.options.chain_call_control.failed_number === this.options.chain_call_control.total_number) {
            Toast.error("There was an error and no datasets were imported into history.");
        } else if (this.options.chain_call_control.failed_number < this.options.chain_call_control.total_number) {
            Toast.warning(
                "Some of the datasets could not be imported into history. Click this to see what was imported.",
                "",
                `${getAppRoot()}histories/view?id=${history_id}`,
            );
        }
        modal.hide();
    }

    templateImportIntoHistoryProgressBar({ history_name }) {
        return `<div class="import_text">
                Importing selected items to history <b>${escape(history_name)}</b>
            </div>
            <div class="progress">
                <div class="progress-bar progress-bar-import" role="progressbar" aria-valuenow="0" aria-valuemin="0"
                    aria-valuemax="100" style="width: 00%;">
                    <span class="completion_span">0% Complete</span>
                </div>
            </div>`;
    }

    templateImportIntoHistoryModal({ histories }) {
        const historyOptions = histories
            .map((history) => `<option value="${escape(history.id)}">${escape(history.name)}</option>`)
            .join("\n");
        return `<div>
                <div class="library-modal-item">
                    Select history:
                    <select name="import_to_history" style="width:50%; margin-bottom: 1em; " autofocus>
                        ${historyOptions}
                    </select>
                </div>
                <div class="library-modal-item">
                    or create new:
                    <input type="text" name="history_name" value=""
                        placeholder="name of the new history" style="width:50%;" />
                </div>
            </div>`;
    }
}

export default {
    ImportDatasetModal: ImportDatasetModal,
};

import axios from "axios";

import { Toast } from "@/composables/toast";
import { getAppRoot } from "@/onload/loadConfig";
import _l from "@/utils/localization";
import Modal from "@/utils/modal";

let progress = 0;
let progressStep = 0;
const chain_call_control = {};

export function updateProgressBar(currentProgress) {
    const progressBar = document.querySelector(".progress-bar-import");
    if (progressBar) {
        progressBar.style.width = `${Math.round(currentProgress)}%`;
    }
    const span = document.querySelector(".completion_span");
    if (span) {
        span.textContent = `${Math.round(currentProgress)}% Complete`;
    }
}

const modal = new Modal();

/**
 * Delete the selected items. Atomic. One by one.
 */
export function deleteSelectedItems(checkedRows, onRemove, refreshTable, refreshTableContent) {
    var dataset_ids = [];
    var folder_ids = [];
    if (checkedRows.length === 0) {
        Toast.info("You must select at least one item for deletion.");
    } else {
        modal.show({
            closing_events: true,
            title: _l("Deleting selected items"),
            body: templateDeletingItemsProgressBar(),
            buttons: {
                Close: () => {
                    modal.hide();
                },
            },
        });
        chain_call_control.total_number = 0;
        chain_call_control.failed_number = 0;
        checkedRows.forEach((row) => {
            const row_id = row.id;
            if (row_id !== undefined) {
                if (row_id.substring(0, 1) == "F") {
                    folder_ids.push(row_id);
                } else {
                    dataset_ids.push(row_id);
                }
            }
        });

        const items_total = dataset_ids.length + folder_ids.length;
        progressStep = 100 / items_total;
        progress = 0;

        var items_to_delete = [];
        for (let i = dataset_ids.length - 1; i >= 0; i--) {
            items_to_delete.push({
                url: `${getAppRoot()}api/libraries/datasets/${dataset_ids[i]}`,
            });
        }
        for (let i = folder_ids.length - 1; i >= 0; i--) {
            items_to_delete.push({
                url: `${getAppRoot()}api/folders/${folder_ids[i]}`,
            });
        }

        chain_call_control.total_number = items_total;
        chainCallDeletingItems(items_to_delete, onRemove, refreshTable, refreshTableContent);
    }
}

function templateDeletingItemsProgressBar() {
    return `<div class="import_text">
            </div>
            <div class="progress">
                <div class="progress-bar progress-bar-import" role="progressbar" aria-valuenow="0" aria-valuemin="0"
                    aria-valuemax="100" style="width: 00%;">
                    <span class="completion_span">0% Complete</span>
                </div>
            </div>`;
}

function chainCallDeletingItems(items_to_delete, onRemove, refreshTable, refreshTableContent) {
    var item_to_delete = items_to_delete.pop();
    if (typeof item_to_delete === "undefined") {
        if (chain_call_control.failed_number === 0) {
            refreshTableContent();
            Toast.success("Selected items were deleted.");
        } else if (chain_call_control.failed_number === chain_call_control.total_number) {
            Toast.error(
                "There was an error and no items were deleted. Please make sure you have sufficient permissions.",
            );
        } else if (chain_call_control.failed_number < chain_call_control.total_number) {
            Toast.warning("Some of the items could not be deleted. Please make sure you have sufficient permissions.");
        }
        modal.hide();
        return;
    }
    const deletePromise = axios.delete(item_to_delete.url);
    refreshTable();
    deletePromise
        .then(({ data }) => {
            onRemove(data);
            updateProgress();
            chainCallDeletingItems(items_to_delete, onRemove, refreshTable, refreshTableContent);
        })
        .catch(() => {
            chain_call_control.failed_number += 1;
            updateProgress();
            chainCallDeletingItems(items_to_delete, onRemove, refreshTable, refreshTableContent);
        });
}

function updateProgress() {
    progress += progressStep;
    updateProgressBar(progress);
}

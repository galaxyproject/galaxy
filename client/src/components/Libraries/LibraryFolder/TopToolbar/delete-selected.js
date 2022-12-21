import { getGalaxyInstance } from "app";
import { Toast } from "composables/toast";
import _l from "utils/localization";
import mod_library_model from "./library-model";
import _ from "underscore";
import $ from "jquery";

let progress = 0;
let items_total = 0;
let progressStep = 0;
const chain_call_control = {};

/**
 * Delete the selected items. Atomic. One by one.
 */
export function deleteSelectedItems(checkedRows, onRemove, refreshTable, refreshTableContent) {
    const Galaxy = getGalaxyInstance();
    var dataset_ids = [];
    var folder_ids = [];
    if (checkedRows.length === 0) {
        Toast.info("You must select at least one item for deletion.");
    } else {
        var template = templateDeletingItemsProgressBar();
        const modal = Galaxy.modal;
        modal.show({
            closing_events: true,
            title: _l("Deleting selected items"),
            body: template({}),
            buttons: {
                Close: () => {
                    Galaxy.modal.hide();
                },
            },
        });
        // init the control counters
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

        // init the progress bar
        items_total = dataset_ids.length + folder_ids.length;
        progressStep = 100 / items_total;
        progress = 0;

        // prepare the dataset items to be added
        var items_to_delete = [];
        for (let i = dataset_ids.length - 1; i >= 0; i--) {
            var dataset = new mod_library_model.Item({
                id: dataset_ids[i],
            });
            items_to_delete.push(dataset);
        }
        for (let i = folder_ids.length - 1; i >= 0; i--) {
            var folder = new mod_library_model.FolderAsModel({
                id: folder_ids[i],
            });
            items_to_delete.push(folder);
        }

        chain_call_control.total_number = items_total;
        // call the recursive function to call ajax one after each other (request FIFO queue)
        chainCallDeletingItems(items_to_delete, onRemove, refreshTable, refreshTableContent);
    }
}

function templateDeletingItemsProgressBar() {
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
}

/**
 * Take the array of lddas, create request for each and
 * call them in chain. Update progress bar in between each.
 */
function chainCallDeletingItems(items_to_delete, onRemove, refreshTable, refreshTableContent) {
    const Galaxy = getGalaxyInstance();
    const deleted_items = new mod_library_model.Folder();
    var item_to_delete = items_to_delete.pop();
    if (typeof item_to_delete === "undefined") {
        if (chain_call_control.failed_number === 0) {
            refreshTableContent();
            Toast.success("Selected items were deleted.");
        } else if (chain_call_control.failed_number === chain_call_control.total_number) {
            Toast.error(
                "There was an error and no items were deleted. Please make sure you have sufficient permissions."
            );
        } else if (chain_call_control.failed_number < chain_call_control.total_number) {
            Toast.warning("Some of the items could not be deleted. Please make sure you have sufficient permissions.");
        }
        Galaxy.modal.hide();
        return deleted_items;
    }
    item_to_delete
        .destroy()
        .done((item) => {
            onRemove(item);
            // TODO remove stuff from table content
            // Galaxy.libraries.folderListView.collection.remove(item_to_delete.id);
            updateProgress();
            // add the deleted item to collection, triggers rendering
            // TODO add to deleted

            chainCallDeletingItems(items_to_delete, onRemove, refreshTable, refreshTableContent);
        })
        .fail(() => {
            chain_call_control.failed_number += 1;
            updateProgress();
            chainCallDeletingItems(items_to_delete, onRemove, refreshTable, refreshTableContent);
        });
    refreshTable();
}

/**
 * Update progress bar in modal.
 */
export function updateProgress() {
    progress += progressStep;
    $(".progress-bar-import").width(`${Math.round(progress)}%`);
    var txt_representation = `${Math.round(progress)}% Complete`;
    $(".completion_span").text(txt_representation);
}

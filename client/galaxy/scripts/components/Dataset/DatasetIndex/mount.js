/**
 * Endpoint for mounting dataset link from non-Vue environment.
 */
import $ from "jquery";
import DatasetIndex from "./DatasetIndex";
import { mountVueComponent } from "utils/mountVueComponent";

export const mountDatasetIndex = (propsData = {}) => {
    $(".dataset-index").each((index, el) => {
        propsData.history_dataset_id = $(el).attr("history_dataset_id");
        propsData.path = $(el).attr("path");
        mountVueComponent(DatasetIndex)(propsData, el);
    });
};

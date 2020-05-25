/**
 * Endpoint for mounting dataset link from non-Vue environment.
 */
import $ from "jquery";
import DatasetLink from "./DatasetLink";
import { mountVueComponent } from "utils/mountVueComponent";

export const mountDatasetLink = (propsData = {}) => {
    $(".dataset-link").each((index, el) => {
        propsData.history_dataset_id = $(el).attr("history_dataset_id");
        propsData.path = $(el).attr("path");
        propsData.label = $(el).attr("label");
        propsData.image = $(el).attr("image");
        mountVueComponent(DatasetLink)(propsData, el);
    });
};

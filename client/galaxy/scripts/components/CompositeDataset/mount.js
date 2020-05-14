/**
 * Endpoint for mounting job metrics from non-Vue environment.
 */
import $ from "jquery";
import CompositeDataset from "./CompositeDataset.vue";
import { mountVueComponent } from "utils/mountVueComponent";

export const mountCompositeDataset = (propsData = {}) => {

    $(".composite-dataset").each((index, el) => {
        propsData.history_dataset_id = $(el).attr("history_dataset_id");
        propsData.path = $(el).attr("path");
        propsData.label = $(el).attr("label");
        propsData.image = $(el).attr("image");
        mountVueComponent(CompositeDataset)(propsData, el);
    });
};

/**
 * Endpoint for mounting job metrics from non-Vue environment.
 */
import DatasetStorage from "./DatasetStorage.vue";
import { mountVueComponent } from "utils/mountVueComponent";

export const mountDatasetStorage = (propsData = {}) => {
    const elements = document.querySelectorAll(".dataset-storage");
    Array.prototype.forEach.call(elements, function (el, i) {
        const datasetId = el.getAttribute("dataset_id");
        const datasetType = el.getAttribute("dataset_type") || "hda";
        propsData.datasetId = datasetId;
        propsData.datasetType = datasetType;
        mountVueComponent(DatasetStorage)(propsData, el);
    });
};

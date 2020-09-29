/**
 * Endpoint for mounting job metrics from non-Vue environment.
 */
import $ from "jquery";
import DatasetInformation from "./DatasetInformation";
import { mountVueComponent } from "utils/mountVueComponent";

export const mountDatasetInformation = (propsData = {}) => {
    $(".dataset-information").each((index, el) => {
        propsData.hda_id = $(el).attr("hda_id");
        mountVueComponent(DatasetInformation)(propsData, el);
    });
};

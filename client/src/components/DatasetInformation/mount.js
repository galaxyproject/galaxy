/**
 * Endpoint for mounting job metrics from non-Vue environment.
 */
import DatasetInformation from "./DatasetInformation";
import { mountVueComponent } from "utils/mountVueComponent";

export const mountDatasetInformation = (propsData = {}) => {
    document.querySelectorAll(".dataset-information").forEach((element) => {
        propsData.hda_id = element.getAttribute("hda_id");
        mountVueComponent(DatasetInformation)(propsData, element);
    });
};

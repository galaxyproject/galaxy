/**
 * Endpoint for mounting dataset components from non-Vue environment.
 */
import $ from "jquery";
import DatasetLink from "./DatasetLink/DatasetLink";
import { mountVueComponent } from "utils/mountVueComponent";
import DatasetIndex from "./DatasetIndex/DatasetIndex";
import DatasetAsImage from "./DatasetAsImage/DatasetAsImage";

export const mountDatasetAsImage = () => {
    return mountDatasetComponent(".dataset-as-image", ["history_dataset_id", "path"], DatasetAsImage);
};
export const mountDatasetIndex = () => {
    return mountDatasetComponent(".dataset-index", ["history_dataset_id", "path"], DatasetIndex);
};
export const mountDatasetLink = () => {
    return mountDatasetComponent(".dataset-link", ["history_dataset_id", "path", "label"], DatasetLink);
};

export const mountDatasetComponents = () => {
    const all = [mountDatasetAsImage, mountDatasetIndex, mountDatasetLink];
    all.forEach((func) => func());
};

const mountDatasetComponent = (selector, props, component, propsData = {}) => {
    $(selector).each((index, el) => {
        props.forEach((prop) => {
            propsData[prop] = $(el).attr(prop);
        });
        mountVueComponent(component)(propsData, el);
    });
};

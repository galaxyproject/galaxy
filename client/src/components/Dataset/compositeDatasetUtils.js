import { getAppRoot } from "onload/loadConfig";
import { Services } from "components/Dataset/services";
import store from "../../store/index";

export const getPathDestination = async (history_dataset_id, path) => {
    const services = new Services({ root: getAppRoot() });

    const computePathDestination = (pathDestination) => {
        if (path === undefined || path === "undefined") {
            return pathDestination;
        }

        const filepath = path;

        const datasetEntry = datasetContent.find((datasetEntry) => {
            return filepath === datasetEntry.path;
        });

        if (datasetEntry) {
            if (datasetEntry.class === "Directory") {
                pathDestination.isDirectory = true;
                pathDestination.filepath = filepath;
                return pathDestination;
            }
            pathDestination.fileLink = services.getCompositeDatasetLink(history_dataset_id, datasetEntry.path);
        }
        return pathDestination;
    };

    let datasetContent = store.getters.getDatasetExtFiles(history_dataset_id);

    if (datasetContent == null) {
        await store.dispatch("fetchDatasetExtFiles", history_dataset_id);
        datasetContent = store.getters.getDatasetExtFiles(history_dataset_id);
    }

    return computePathDestination({ datasetContent: datasetContent });
};

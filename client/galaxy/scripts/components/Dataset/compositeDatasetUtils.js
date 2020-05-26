import { getAppRoot } from "onload/loadConfig";
import { Services } from "components/Dataset/services";

export const getPathDestination = (history_dataset_id, path) => {
    const services = new Services({ root: getAppRoot() });
    return services.getCompositeDatasetContentFiles(history_dataset_id).then((datasetContent) => {
        const pathDestination = { datasetContent: datasetContent };
        if (datasetContent[0].class === "Directory") pathDestination.datasetRootDir = datasetContent[0].path;
        else return;

        if (path === undefined || path === "undefined") {
            return pathDestination;
        }

        const filepath = `${pathDestination.datasetRootDir}/${path}`;

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
    });
};

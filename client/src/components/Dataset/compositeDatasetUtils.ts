import { DatasetExtraFiles, getCompositeDatasetLink } from "@/api/datasets";
import { useDatasetExtraFilesStore } from "@/stores/datasetExtraFilesStore";

interface PathDestination {
    datasetContent: DatasetExtraFiles;
    isDirectory: boolean;
    filepath?: string;
    fileLink?: string;
}

export async function getPathDestination(dataset_id: string, path?: string): Promise<PathDestination | null> {
    const datasetExtraFilesStore = useDatasetExtraFilesStore();

    let datasetExtraFiles = datasetExtraFilesStore.getDatasetExtraFiles(dataset_id);
    if (!datasetExtraFiles) {
        await datasetExtraFilesStore.fetchDatasetExtFilesByDatasetId({ id: dataset_id });
        datasetExtraFiles = datasetExtraFilesStore.getDatasetExtraFiles(dataset_id);
    }

    if (datasetExtraFiles === null) {
        return null;
    }

    const pathDestination: PathDestination = { datasetContent: datasetExtraFiles, isDirectory: false, filepath: path };

    if (path === undefined || path === "undefined") {
        return pathDestination;
    }

    const filepath = path;

    const datasetEntry = datasetExtraFiles?.find((entry) => {
        return filepath === entry.path;
    });

    if (datasetEntry) {
        if (datasetEntry.class === "Directory") {
            pathDestination.isDirectory = true;
            pathDestination.filepath = filepath;
            return pathDestination;
        }
        pathDestination.fileLink = getCompositeDatasetLink(dataset_id, datasetEntry.path);
    }
    return pathDestination;
}

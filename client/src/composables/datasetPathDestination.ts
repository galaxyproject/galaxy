import { computed, ref, set } from "vue";

import { type DatasetExtraFiles, getCompositeDatasetLink } from "@/api/datasets";
import { useDatasetExtraFilesStore } from "@/stores/datasetExtraFilesStore";

export interface PathDestination {
    datasetContent: DatasetExtraFiles;
    isDirectory: boolean;
    filepath?: string;
    fileLink?: string;
}

interface PathDestinationMap {
    [key: string]: PathDestination;
}

export function useDatasetPathDestination() {
    const datasetExtraFilesStore = useDatasetExtraFilesStore();

    const cache = ref<{ [key: string]: PathDestinationMap }>({});

    const datasetPathDestination = computed(() => {
        return (dataset_id: string, path?: string) => {
            const targetPath = path ?? "undefined";
            const pathDestination = cache.value[dataset_id]?.[targetPath];
            if (!pathDestination) {
                getPathDestination(dataset_id, path);
            }
            return pathDestination ?? null;
        };
    });

    async function getPathDestination(dataset_id: string, path?: string): Promise<PathDestination | null> {
        let datasetExtraFiles = datasetExtraFilesStore.getDatasetExtraFiles(dataset_id);
        if (!datasetExtraFiles) {
            await datasetExtraFilesStore.fetchDatasetExtFilesByDatasetId({ id: dataset_id });
            datasetExtraFiles = datasetExtraFilesStore.getDatasetExtraFiles(dataset_id);
        }

        if (datasetExtraFiles === null) {
            return null;
        }

        const pathDestination: PathDestination = {
            datasetContent: datasetExtraFiles,
            isDirectory: false,
            filepath: path,
        };

        if (path === undefined || path === "undefined") {
            set(cache.value, dataset_id, { ["undefined"]: pathDestination });
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

        set(cache.value, dataset_id, { [path]: pathDestination });

        return pathDestination;
    }

    return { datasetPathDestination };
}

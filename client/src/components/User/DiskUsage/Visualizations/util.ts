import { library } from "@fortawesome/fontawesome-svg-core";
import { faAngleDoubleDown, faAngleDoubleUp } from "@fortawesome/free-solid-svg-icons";
import { computed, onMounted, ref } from "vue";

import { useConfirmDialog } from "@/composables/confirmDialog";
import { useToast } from "@/composables/toast";
import localize from "@/utils/localization";

import { type DataValuePoint } from "./Charts";
import { bytesLabelFormatter, bytesValueFormatter } from "./Charts/formatters";
import { type ItemSizeSummary, purgeDatasetById, undeleteDatasetById } from "./service";

library.add(faAngleDoubleUp, faAngleDoubleDown);

interface DataLoader {
    (): Promise<void>;
}

interface DataReload {
    (): void;
}

export function useDatasetsToDisplay() {
    const numberOfDatasetsToDisplayOptions = [10, 20, 50];
    const numberOfDatasetsToDisplay = ref<number>(numberOfDatasetsToDisplayOptions[0] || 10);
    const numberOfDatasetsLimit = Math.max(...numberOfDatasetsToDisplayOptions);
    const datasetsSizeSummaryMap = new Map<string, ItemSizeSummary>();
    const topNDatasetsBySizeData = ref<DataValuePoint[] | null>(null);

    function isRecoverableDataPoint(dataPoint?: DataValuePoint): boolean {
        if (dataPoint) {
            const datasetSizeSummary = datasetsSizeSummaryMap.get(dataPoint.id || "");
            return datasetSizeSummary?.deleted || dataPoint.id === "deleted";
        }
        return false;
    }

    const { success: successToast, error: errorToast } = useToast();
    const { confirm } = useConfirmDialog();

    async function onUndeleteDataset(reloadData: DataReload, datasetId: string) {
        try {
            const result = await undeleteDatasetById(datasetId);
            const dataset = datasetsSizeSummaryMap.get(datasetId);
            if (dataset && !result.deleted) {
                dataset.deleted = result.deleted;
                datasetsSizeSummaryMap.set(datasetId, dataset);
                successToast(localize("Dataset undeleted successfully."));
                reloadData();
            }
        } catch (error) {
            errorToast(`${error}`, localize("An error occurred while undeleting the dataset."));
        }
    }

    async function onPermanentlyDeleteDataset(reloadData: DataReload, datasetId: string) {
        const confirmed = await confirm(
            localize("Are you sure you want to permanently delete this dataset? This action cannot be undone."),
            {
                title: localize("Permanently delete dataset?"),
                okVariant: "danger",
                okTitle: localize("Permanently delete"),
                cancelTitle: localize("Cancel"),
            }
        );
        if (!confirmed) {
            return;
        }
        try {
            const result = await purgeDatasetById(datasetId);
            const dataset = datasetsSizeSummaryMap.get(datasetId);
            if (dataset && result) {
                datasetsSizeSummaryMap.delete(datasetId);
                successToast(localize("Dataset permanently deleted successfully."));
                reloadData();
            }
        } catch (error) {
            errorToast(`${error}`, localize("An error occurred while permanently deleting the dataset."));
        }
    }

    return {
        numberOfDatasetsToDisplayOptions,
        numberOfDatasetsToDisplay,
        numberOfDatasetsLimit,
        datasetsSizeSummaryMap,
        topNDatasetsBySizeData,
        isRecoverableDataPoint,
        onUndeleteDataset,
        onPermanentlyDeleteDataset,
    };
}

export function useDataLoading() {
    const isLoading = ref(true);

    const loadDataOnMount = (dataLoader: DataLoader) => {
        onMounted(async () => {
            isLoading.value = true;
            await dataLoader();
            isLoading.value = false;
        });
    };
    return {
        isLoading,
        loadDataOnMount,
    };
}

export function buildTopNDatasetsBySizeData(datasetsSizeSummary: ItemSizeSummary[], n: number): DataValuePoint[] {
    const topTenDatasetsBySize = datasetsSizeSummary.sort((a, b) => b.size - a.size).slice(0, n);
    return topTenDatasetsBySize.map((dataset) => ({
        id: dataset.id,
        label: dataset.name,
        value: dataset.size,
    }));
}

export const byteFormattingForChart = {
    "enable-selection": true,
    labelFormatter: bytesLabelFormatter,
    valueFormatter: bytesValueFormatter,
};

export function useAdvancedFiltering() {
    const isAdvanced = ref<boolean>(false);

    function toggleAdvanced() {
        isAdvanced.value = !isAdvanced.value;
    }

    const inputGroupClasses = computed(() => {
        return ["float-right", "auto"];
    });

    return {
        faAngleDoubleUp,
        faAngleDoubleDown,
        isAdvanced,
        inputGroupClasses,
        toggleAdvanced,
    };
}

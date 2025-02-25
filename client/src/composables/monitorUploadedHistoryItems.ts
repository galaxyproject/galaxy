import { faExclamation, faSpinner, type IconDefinition } from "@fortawesome/free-solid-svg-icons";
import { computed, type Ref } from "vue";

import { type HDASummary, type HistoryItemSummary, isHDA } from "@/api";
import { useHistoryItemsStore } from "@/stores/historyItemsStore";
import { stateIsTerminal } from "@/utils/utils";

const REFER_TO_HISTORY_MSG = "Refer to the history panel to view dataset state.";

/**
 * For given uploaded items, monitor the states of those items from the history.
 *
 * @param uploadValues - The uploaded values from the upload `DefaultBox`
 * @param historyId - The ID of the history being uploaded to
 * @param enableStart - If an upload is enabled to start
 * @param creatingPairedType - If the user has selected to create a `paired`
 *                             or `list:paired` collection JUST from these uploads
 */
export function monitorUploadedHistoryItems(
    uploadValues: Ref<{ outputs: unknown }[]>,
    historyId: Ref<string>,
    enableStart: Ref<boolean>,
    creatingPairedType: Ref<boolean>
) {
    const historyItemsStore = useHistoryItemsStore();
    /** Uploaded items from the history */
    const uploadedHistoryItems = computed(() => {
        // Get all successfully uploaded datasets
        const uploadedDatasets: HistoryItemSummary[] = [];
        uploadValues.value.forEach((model) => {
            const outputs = model.outputs;
            if (outputs) {
                Object.entries(outputs).forEach((output) => {
                    const outputDetails = output[1] as HistoryItemSummary;
                    uploadedDatasets.push(outputDetails);
                });
            }
        });

        // Get uploaded datasets from history
        const historyItems = historyItemsStore.getHistoryItems(historyId.value, "");
        return uploadedDatasets
            .map((item) => historyItems.find((historyItem) => historyItem.id === item.id))
            .filter((item) => isHDA(item)) as HDASummary[];
    });

    const uploadedHistoryItemsReady = computed(() =>
        uploadedHistoryItems.value.every((item) => item && stateIsTerminal(item))
    );

    const uploadedHistoryItemsOk = computed(() =>
        uploadedHistoryItems.value.filter((item) => item && item.state === "ok")
    );

    const historyItemsStateInfo = computed<{
        variant: string;
        message: string;
        icon?: IconDefinition;
        spin?: boolean;
    } | null>(() => {
        if (uploadedHistoryItems.value?.length && !enableStart.value) {
            if (!uploadedHistoryItemsReady.value) {
                return {
                    variant: "info",
                    message: `Your upload(s) are not ready to be used yet. ${REFER_TO_HISTORY_MSG}`,
                    icon: faSpinner,
                    spin: true,
                };
            } else if (uploadedHistoryItems.value.length > uploadedHistoryItemsOk.value.length) {
                return {
                    variant: "warning",
                    message: `Only ${uploadedHistoryItemsOk.value.length} / ${uploadedHistoryItems.value.length} uploaded items are usable. ${REFER_TO_HISTORY_MSG}`,
                    icon: faExclamation,
                };
            } else if (creatingPairedType.value && uploadedHistoryItemsOk.value.length % 2 !== 0) {
                return {
                    variant: "danger",
                    message:
                        "Please upload an even number of datasets to create a dataset pair or a list of dataset pairs.",
                    icon: faExclamation,
                };
            } else if (uploadedHistoryItemsOk.value.length) {
                return {
                    variant: "success",
                    message: "Upload(s) ready to be used.",
                };
            } else {
                return null;
            }
        } else {
            return null;
        }
    });

    return {
        /** Uploaded history items with the `ok` state */
        uploadedHistoryItemsOk,
        /** If all uploaded history items have achieved a terminal state */
        uploadedHistoryItemsReady,
        historyItemsStateInfo,
    };
}

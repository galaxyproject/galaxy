import { faExclamation, faSpinner, type IconDefinition } from "@fortawesome/free-solid-svg-icons";
import { computed, type Ref } from "vue";

import { type HDASummary, type HistoryItemSummary, isHDA } from "@/api";
import type { ComponentColor } from "@/components/BaseComponents/componentVariants";
import type { UploadItem } from "@/components/Upload/model";
import STATES from "@/mvc/dataset/states";
import { useHistoryItemsStore } from "@/stores/historyItemsStore";

const REFER_TO_HISTORY_MSG = "Refer to the history panel to view dataset state.";

/** Terminal states that are not usable from an upload (anything but `ok` or `deferred`)
 */
const UNUSABLE_FROM_UPLOAD_STATES = Object.values(STATES.READY_STATES).filter(
    (state) => state !== STATES.OK && state !== STATES.DEFERRED
);

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
    uploadValues: Ref<UploadItem[]>,
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
            // Some uploads (e.g.: in the case of remote file upload) may have the entire set of uploaded files
            // in the `outputs` object, while typically, the `outputs` object contains each individual upload.
            if (outputs) {
                Object.entries(outputs).forEach((output) => {
                    const outputDetails = output[1] as HistoryItemSummary;
                    // Since there is a possibility of all uploads being in the `outputs` object,
                    // we need to ensure that we only add unique datasets to the list.
                    if (!uploadedDatasets.some((item) => item.id === outputDetails.id)) {
                        uploadedDatasets.push(outputDetails);
                    }
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
        uploadedHistoryItems.value.every((item) => item && item.extension !== "auto")
    );

    // TODO: Could be refactored to use `useCollectionCreator.isElementInvalid()` instead? (with the added `auto` check)
    const uploadedHistoryItemsOk = computed(() =>
        uploadedHistoryItems.value.filter(
            (item) => item && !UNUSABLE_FROM_UPLOAD_STATES.includes(item.state) && item.extension !== "auto"
        )
    );

    const historyItemsStateInfo = computed<{
        color?: ComponentColor;
        message: string;
        icon?: IconDefinition;
        spin?: boolean;
    } | null>(() => {
        if (!enableStart.value && uploadValues.value.length) {
            if (!uploadedHistoryItems.value?.length) {
                return {
                    color: "blue",
                    message: `Dataset(s) not uploaded yet. ${REFER_TO_HISTORY_MSG}`,
                    icon: faSpinner,
                    spin: true,
                };
            } else if (!uploadedHistoryItemsReady.value) {
                return {
                    color: "blue",
                    message: `Waiting for upload(s) to have valid extension(s). ${REFER_TO_HISTORY_MSG}`,
                    icon: faSpinner,
                    spin: true,
                };
            } else if (uploadedHistoryItems.value.length > uploadedHistoryItemsOk.value.length) {
                return {
                    color: "orange",
                    message: `Only ${uploadedHistoryItemsOk.value.length} / ${uploadedHistoryItems.value.length} uploaded items are usable. ${REFER_TO_HISTORY_MSG}`,
                    icon: faExclamation,
                };
            } else if (creatingPairedType.value && uploadedHistoryItemsOk.value.length % 2 !== 0) {
                return {
                    color: "red",
                    message:
                        "Please upload an even number of datasets to create a dataset pair or a list of dataset pairs.",
                    icon: faExclamation,
                };
            } else if (uploadedHistoryItemsOk.value.length) {
                return {
                    color: "blue", // Not "green" because this is for a `GButton`, that is ready
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

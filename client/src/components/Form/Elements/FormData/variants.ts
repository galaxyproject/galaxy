import { faCopy, faFile, faFolder } from "@fortawesome/free-regular-svg-icons";
import type { IconDefinition } from "font-awesome-6";

/** Data input variations interface */
export interface VariantInterface {
    batch: string;
    icon: IconDefinition;
    library?: boolean;
    multiple: boolean;
    src: string;
    tooltip: string;
}

/** Batch mode variations */
export const BATCH = { DISABLED: "disabled", ENABLED: "enabled", LINKED: "linked" };

/** Data source variations */
export const SOURCE = { DATASET: "hda", COLLECTION: "hdca", COLLECTION_ELEMENT: "dce", LIBRARY_DATASET: "ldda" };

/** List of available data input variations */
export const VARIANTS: Record<string, Array<VariantInterface>> = {
    data: [
        {
            src: SOURCE.DATASET,
            icon: faFile,
            tooltip: "Single dataset",
            library: true,
            multiple: false,
            batch: BATCH.DISABLED,
        },
        {
            src: SOURCE.DATASET,
            icon: faCopy,
            tooltip: "Multiple datasets",
            multiple: true,
            batch: BATCH.LINKED,
        },
        {
            src: SOURCE.COLLECTION,
            icon: faFolder,
            tooltip: "Dataset collection",
            multiple: false,
            batch: BATCH.LINKED,
        },
    ],
    data_multiple: [
        {
            src: SOURCE.DATASET,
            icon: faCopy,
            tooltip: "Multiple datasets",
            library: true,
            multiple: true,
            batch: BATCH.DISABLED,
        },
        {
            src: SOURCE.COLLECTION,
            icon: faFolder,
            tooltip: "Dataset collection",
            multiple: true,
            batch: BATCH.DISABLED,
        },
    ],
    data_collection: [
        {
            src: SOURCE.COLLECTION,
            icon: faFolder,
            tooltip: "Dataset collection",
            multiple: false,
            batch: BATCH.DISABLED,
        },
    ],
    workflow_data: [
        {
            src: SOURCE.DATASET,
            icon: faFile,
            tooltip: "Single dataset",
            multiple: false,
            batch: BATCH.DISABLED,
        },
    ],
    workflow_data_multiple: [
        {
            src: SOURCE.DATASET,
            icon: faCopy,
            tooltip: "Multiple datasets",
            multiple: true,
            batch: BATCH.DISABLED,
        },
    ],
    workflow_data_collection: [
        {
            src: SOURCE.COLLECTION,
            icon: faFolder,
            tooltip: "Dataset collection",
            multiple: false,
            batch: BATCH.DISABLED,
        },
    ],
    module_data: [
        {
            src: SOURCE.DATASET,
            icon: faFile,
            tooltip: "Single dataset",
            multiple: false,
            batch: BATCH.DISABLED,
        },
        {
            src: SOURCE.DATASET,
            icon: faCopy,
            tooltip: "Multiple datasets",
            multiple: true,
            batch: BATCH.ENABLED,
        },
    ],
    module_data_collection: [
        {
            src: SOURCE.COLLECTION,
            icon: faFolder,
            tooltip: "Dataset collection",
            multiple: false,
            batch: BATCH.DISABLED,
        },
        {
            src: SOURCE.COLLECTION,
            icon: faFolder,
            tooltip: "Multiple collections",
            multiple: true,
            batch: BATCH.ENABLED,
        },
    ],
};

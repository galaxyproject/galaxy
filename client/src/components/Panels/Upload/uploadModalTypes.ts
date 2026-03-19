import type { DataOption } from "@/components/Form/Elements/FormData/types";
import type { UploadedDataset } from "@/composables/upload/uploadItemTypes";

import type { UploadMethod } from "./types";

export type { UploadedDataset } from "@/composables/upload/uploadItemTypes";

/**
 * Subset of UploadMethod that directly creates new datasets in the history.
 * These are the basic upload methods available in the upload modal.
 */
export type DatasetUploadMethod = Extract<
    UploadMethod,
    "local-file" | "paste-content" | "paste-links" | "remote-files" | "data-library"
>;

/**
 * Configuration options for the upload modal.
 */
export interface UploadModalConfig {
    /** List of upload methods that users can select from. */
    allowedMethods?: DatasetUploadMethod[];
    /** Whether to allow creating dataset collections. */
    allowCollections?: boolean;
    /** Allowed file format extensions. */
    formats?: string[];
    /** Whether multiple files can be uploaded at once. */
    multiple?: boolean;
    /** Target history ID where datasets will be uploaded. */
    targetHistoryId?: string;
    /** Custom title for the upload modal. */
    title?: string;
    /** Whether to hide user tips/help text. */
    hideTips?: boolean;
}

/**
 * Result returned when the upload modal is closed.
 */
export interface UploadModalResult {
    /** List of datasets that were uploaded. */
    datasets: UploadedDataset[];
    /** Whether the user cancelled the upload operation. */
    cancelled: boolean;
    /** Function to convert uploaded datasets to form data options. */
    toDataOptions: () => DataOption[];
}

/**
 * Promise resolvers for handling the upload modal result.
 */
export interface UploadModalResolvers {
    /** Resolve the promise with the upload result. */
    resolve: (result: UploadModalResult) => void;
    /** Reject the promise if the upload fails. */
    reject: (reason?: unknown) => void;
}

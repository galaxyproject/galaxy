import type { RouteLocationNormalized, RouteLocationRaw } from "vue-router";

export interface ZipImportCounts {
    workflowFileCount: number;
    regularFileCount: number;
}

/** Where the wizard sends the user once the import has started. */
export function zipImportResultsLocation(counts: ZipImportCounts): RouteLocationRaw {
    return {
        name: "ZipImportResults",
        params: {
            workflowFileCount: String(counts.workflowFileCount),
            regularFileCount: String(counts.regularFileCount),
        },
    };
}

/** Props for the results page, read back from that location. */
export function zipImportResultsProps(route: RouteLocationNormalized): ZipImportCounts {
    return {
        workflowFileCount: Number(route.params.workflowFileCount),
        regularFileCount: Number(route.params.regularFileCount),
    };
}

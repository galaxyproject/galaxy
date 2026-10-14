import type { RouteLocationNormalized, RouteLocationRaw } from "vue-router";

export interface ZipImportCounts {
    workflowFileCount: number;
    regularFileCount: number;
}

/** Where the wizard sends the user once the import has started. */
export function zipImportResultsLocation(counts: ZipImportCounts): RouteLocationRaw {
    // The route's path declares no params, and vue-router 4 drops undeclared ones, so the counts go in the query.
    return {
        name: "ZipImportResults",
        query: {
            workflowFileCount: String(counts.workflowFileCount),
            regularFileCount: String(counts.regularFileCount),
        },
    };
}

/** Props for the results page, read back from that location. */
export function zipImportResultsProps(route: RouteLocationNormalized): ZipImportCounts {
    return {
        workflowFileCount: Number(route.query.workflowFileCount),
        regularFileCount: Number(route.query.regularFileCount),
    };
}

import type { Route } from "vue-router";

/** The TRS import parameters of a `/workflows/trs_import` or `/workflows/import` URL. */
export function trsImportQuery(query: Route["query"]) {
    return {
        trsId: query.trs_id as string | undefined,
        trsUrl: query.trs_url as string | undefined,
        trsServer: query.trs_server as string | undefined,
        trsVersionId: (query.trs_version ?? query.trs_version_id) as string | undefined,
        isRun: query.run_form === "true",
    };
}

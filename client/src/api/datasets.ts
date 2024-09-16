import axios from "axios";
import type { FetchArgType } from "openapi-typescript-fetch";

import { HDADetailed } from "@/api";
import { components, fetcher } from "@/api/schema";
import { withPrefix } from "@/utils/redirect";

export const datasetsFetcher = fetcher.path("/api/datasets").method("get").create();

type GetDatasetsApiOptions = FetchArgType<typeof datasetsFetcher>;
type GetDatasetsQuery = Pick<GetDatasetsApiOptions, "limit" | "offset">;
// custom interface for how we use getDatasets
interface GetDatasetsOptions extends GetDatasetsQuery {
    sortBy?: string;
    sortDesc?: boolean;
    query?: string;
}

/** Datasets request helper **/
export async function getDatasets(options: GetDatasetsOptions = {}) {
    const params: GetDatasetsApiOptions = {};
    if (options.sortBy) {
        const sortPrefix = options.sortDesc ? "-dsc" : "-asc";
        params.order = `${options.sortBy}${sortPrefix}`;
    }
    if (options.limit) {
        params.limit = options.limit;
    }
    if (options.offset) {
        params.offset = options.offset;
    }
    if (options.query) {
        params.q = ["name-contains"];
        params.qv = [options.query];
    }
    const { data } = await datasetsFetcher(params);
    return data;
}

export const fetchDataset = fetcher.path("/api/datasets/{dataset_id}").method("get").create();

export const fetchDatasetStorage = fetcher.path("/api/datasets/{dataset_id}/storage").method("get").create();

export async function fetchDatasetDetails(params: { id: string }): Promise<HDADetailed> {
    const { data } = await fetchDataset({ dataset_id: params.id, view: "detailed" });
    // We know that the server will return a DatasetDetails object because of the view parameter
    // but the type system doesn't, so we have to cast it.
    return data as unknown as HDADetailed;
}

const updateDataset = fetcher.path("/api/datasets/{dataset_id}").method("put").create();

export async function undeleteDataset(datasetId: string) {
    const { data } = await updateDataset({
        dataset_id: datasetId,
        type: "dataset",
        deleted: false,
    });
    return data;
}

const deleteDataset = fetcher.path("/api/datasets/{dataset_id}").method("delete").create();

export async function purgeDataset(datasetId: string) {
    const { data } = await deleteDataset({ dataset_id: datasetId, purge: true });
    return data;
}

const datasetCopy = fetcher.path("/api/histories/{history_id}/contents/{type}s").method("post").create();
type HistoryContentsArgs = FetchArgType<typeof datasetCopy>;
export async function copyDataset(
    datasetId: HistoryContentsArgs["content"],
    historyId: HistoryContentsArgs["history_id"],
    type: HistoryContentsArgs["type"] = "dataset",
    source: HistoryContentsArgs["source"] = "hda"
) {
    const response = await datasetCopy({
        history_id: historyId,
        type,
        source: source,
        content: datasetId,
    });
    return response.data;
}

export function getCompositeDatasetLink(historyDatasetId: string, path: string) {
    return withPrefix(`/api/datasets/${historyDatasetId}/display?filename=${path}`);
}

export type DatasetExtraFiles = components["schemas"]["DatasetExtraFiles"];
export const fetchDatasetExtraFiles = fetcher.path("/api/datasets/{dataset_id}/extra_files").method("get").create();

export async function fetchDatasetAttributes(datasetId: string) {
    const { data } = await axios.get(withPrefix(`/dataset/get_edit?dataset_id=${datasetId}`));

    return data;
}

export type HistoryContentType = components["schemas"]["HistoryContentType"];
export type HistoryContentSource = components["schemas"]["HistoryContentSource"];

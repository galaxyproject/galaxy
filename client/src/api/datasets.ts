import type { FetchArgType } from "openapi-typescript-fetch";

import { DatasetDetails } from "@/api";
import { fetcher } from "@/api/schema";
import { withPrefix } from "@/utils/redirect";

export const datasetsFetcher = fetcher.path("/api/datasets").method("get").create();

type GetDatasetsApiOptions = FetchArgType<typeof datasetsFetcher>;
type GetDatasetsQuery = Pick<GetDatasetsApiOptions, "limit" | "offset">;
// custom interface for how we use getDatasets
interface GetDatasetsOptions extends GetDatasetsQuery {
    sortBy?: string;
    sortDesc?: string;
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

const getDataset = fetcher.path("/api/datasets/{dataset_id}").method("get").create();

export async function fetchDatasetDetails(params: { id: string }): Promise<DatasetDetails> {
    const { data } = await getDataset({ dataset_id: params.id, view: "detailed" });
    // We know that the server will return a DatasetDetails object because of the view parameter
    // but the type system doesn't, so we have to cast it.
    return data as unknown as DatasetDetails;
}

const updateHistoryDataset = fetcher.path("/api/histories/{history_id}/contents/{type}s/{id}").method("put").create();

export async function undeleteHistoryDataset(historyId: string, datasetId: string) {
    const { data } = await updateHistoryDataset({
        history_id: historyId,
        id: datasetId,
        type: "dataset",
        deleted: false,
    });
    return data;
}

const deleteHistoryDataset = fetcher
    .path("/api/histories/{history_id}/contents/{type}s/{id}")
    .method("delete")
    .create();

export async function purgeHistoryDataset(historyId: string, datasetId: string) {
    const { data } = await deleteHistoryDataset({ history_id: historyId, id: datasetId, type: "dataset", purge: true });
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

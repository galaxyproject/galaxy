import type { FetchArgType } from "openapi-typescript-fetch";
import { fetcher } from "@/schema";
import { withPrefix } from "@/utils/redirect";

const _getDatasets = fetcher.path("/api/datasets").method("get").create();
type GetDatasetsApiOptions = FetchArgType<typeof _getDatasets>;
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
    const { data } = await _getDatasets(params);
    return data;
}

const _copyDataset = fetcher.path("/api/histories/{history_id}/contents/{type}s").method("post").create();
type HistoryContentsArgs = FetchArgType<typeof _copyDataset>;
export async function copyDataset(
    datasetId: HistoryContentsArgs["content"],
    historyId: HistoryContentsArgs["history_id"],
    type: HistoryContentsArgs["type"] = "dataset",
    source: HistoryContentsArgs["source"] = "hda"
) {
    const response = await _copyDataset({
        history_id: historyId,
        type,
        source: source,
        content: datasetId,
    });
    return response.data;
}

const _updateTags = fetcher.path("/api/tags").method("put").create();
type UpdateTagsArgs = FetchArgType<typeof _updateTags>;
export async function updateTags(
    itemId: UpdateTagsArgs["item_id"],
    itemClass: UpdateTagsArgs["item_class"],
    itemTags: UpdateTagsArgs["item_tags"]
) {
    const { data } = await _updateTags({
        item_id: itemId,
        item_class: itemClass,
        item_tags: itemTags,
    });
    return data;
}

export function getCompositeDatasetLink(historyDatasetId: string, path: string) {
    // TODO: historyDatasetId is wrong here, we should expose the route without forcing to provide a history id
    return withPrefix(`/api/histories/${historyDatasetId}/contents/${historyDatasetId}/display?filename=${path}`);
}

const getDataset = fetcher.path("/api/histories/{history_id}/contents/{id}").method("get").create();
export async function getCompositeDatasetInfo(id: string) {
    // TODO: ${id} as history id is wrong here, we should expose the route without forcing to provide a history id
    const { data } = await getDataset({ history_id: id, id });
    return data;
}

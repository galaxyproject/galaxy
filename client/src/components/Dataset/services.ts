import { fetcher } from "schema";
import { safePath } from "utils/redirect";
import type { paths } from "schema";

const _getDatasets = fetcher.path("/api/datasets").method("get").create();
type GetDatasetsApiOptions = NonNullable<paths["/api/datasets"]["get"]["parameters"]>["query"];
type GetDatasetsQuery = Pick<NonNullable<GetDatasetsApiOptions>, "limit" | "offset">;
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
        params.order = `${options.sortBy}${sortPrefix}&`;
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
type HistoryContentsPost = paths["/api/histories/{history_id}/contents/{type}s"]["post"];
export async function copyDataset(
    datasetId: HistoryContentsPost["requestBody"]["content"]["application/json"]["content"],
    historyId: HistoryContentsPost["parameters"]["path"]["history_id"],
    type: HistoryContentsPost["parameters"]["path"]["type"] = "dataset",
    source: HistoryContentsPost["requestBody"]["content"]["application/json"]["source"] = "hda"
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
type UpdateTagsBodyParams = paths["/api/tags"]["put"]["requestBody"]["content"]["application/json"];
export async function updateTags(
    itemId: UpdateTagsBodyParams["item_id"],
    itemClass: UpdateTagsBodyParams["item_class"],
    itemTags: UpdateTagsBodyParams["item_tags"]
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
    return safePath(`/api/histories/${historyDatasetId}/contents/${historyDatasetId}/display?filename=${path}`);
}

const getDataset = fetcher.path("/api/histories/{history_id}/contents/{id}").method("get").create();
export async function getCompositeDatasetInfo(id: string) {
    // TODO: ${id} as history id is wrong here, we should expose the route without forcing to provide a history id
    const { data } = await getDataset({ history_id: id, id });
    return data;
}

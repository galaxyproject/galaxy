import axios from "axios";
import { safePath } from "utils/redirect";
import { rethrowSimple } from "utils/simple-error";

/** Datasets request helper **/
export class Services {
    async getDatasets(options = {}) {
        let params = "";
        if (options.sortBy) {
            const sortPrefix = options.sortDesc ? "-dsc" : "-asc";
            params += `order=${options.sortBy}${sortPrefix}&`;
        }
        if (options.limit) {
            params += `limit=${options.limit}&`;
        }
        if (options.offset) {
            params += `offset=${options.offset}&`;
        }
        if (options.query) {
            params += `q=name-contains&qv=${options.query}&`;
        }
        const url = `/api/datasets?${params}`;
        try {
            const { data } = await axios.get(safePath(url));
            return data;
        } catch (e) {
            rethrowSimple(e);
        }
    }

    async copyDataset(datasetId, historyId, type = "dataset", source = "hda") {
        const url = `/api/histories/${historyId}/contents`;
        try {
            const response = await axios.post(safePath(url), {
                type: type,
                source: source,
                content: datasetId,
            });
            return response.data;
        } catch (e) {
            rethrowSimple(e);
        }
    }

    async updateTags(itemId, itemClass, itemTags) {
        const url = `/api/tags`;
        try {
            const response = await axios.put(safePath(url), {
                item_id: itemId,
                item_class: itemClass,
                item_tags: itemTags,
            });
            return response.data;
        } catch (e) {
            rethrowSimple(e);
        }
    }

    getCompositeDatasetLink(historyDatasetId, path) {
        return safePath(`/api/histories/${historyDatasetId}/contents/${historyDatasetId}/display?filename=${path}`);
    }

    async getCompositeDatasetInfo(id) {
        const url = `/api/histories/${id}/contents/${id}`;
        try {
            const response = await axios.get(safePath(url));
            return response.data;
        } catch (e) {
            rethrowSimple(e);
        }
    }
}

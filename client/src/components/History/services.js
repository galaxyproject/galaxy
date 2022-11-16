import axios from "axios";
import { safePath } from "utils/redirect";
import { rethrowSimple } from "utils/simple-error";

export async function getPublishedHistories(options = {}) {
    let params = "view=summary&keys=username,username_and_slug&";
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
    const url = `/api/histories/published?${params}`;
    try {
        const { data } = await axios.get(safePath(url));
        return data;
    } catch (e) {
        rethrowSimple(e);
    }
}

export async function updateTags(itemId, itemClass, itemTags) {
    const url = "/api/tags";
    try {
        const { data } = await axios.put(safePath(url), {
            item_id: itemId,
            item_class: itemClass,
            item_tags: itemTags,
        });
        return data;
    } catch (e) {
        rethrowSimple(e);
    }
}

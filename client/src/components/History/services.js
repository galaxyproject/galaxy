import axios from "axios";
import { safePath } from "utils/redirect";
import { rethrowSimple } from "utils/simple-error";

export async function getPublishedHistories({ limit, offset, sortBy, sortDesc, filterText }, filters) {
    const queryString = filters.getQueryString(filterText);
    let params = `view=summary&keys=username,username_and_slug&offset=${offset}&limit=${limit}`;
    if (sortBy) {
        const sortPrefix = sortDesc ? "-dsc" : "-asc";
        params += `&order=${sortBy}${sortPrefix}`;
    }
    const url = `/api/histories/published?${params}&${queryString}`;
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

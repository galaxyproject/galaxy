import axios from "axios";
import { safePath } from "utils/redirect";
import { rethrowSimple } from "utils/simple-error";
import { getQueryDict } from "store/historyStore/model/filtering";

const getQueryString = (filterText) => {
    const filterDict = getQueryDict(filterText, false);
    return Object.entries(filterDict)
        .map(([f, v]) => `q=${f}&qv=${v}`)
        .join("&");
};

export async function getPublishedHistories({ limit, offset, sortBy, sortDesc, filterText }) {
    const queryString = getQueryString(filterText);
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

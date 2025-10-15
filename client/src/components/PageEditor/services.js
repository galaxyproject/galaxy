import axios from "axios";
import { getAppRoot } from "onload/loadConfig";
import { rethrowSimple } from "utils/simple-error";

export async function save(pageId, content, showProgress = true) {
    try {
        const response = await axios
            .post(`${getAppRoot()}api/pages/${pageId}/revisions`, { content: content })
            .finally();
        return response;
    } catch (e) {
        rethrowSimple(e);
    }
}

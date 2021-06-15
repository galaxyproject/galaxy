import axios from "axios";
import _l from "utils/localization";
import { getAppRoot } from "onload/loadConfig";
import { show_modal, hide_modal } from "layout/modal";
import { rethrowSimple } from "utils/simple-error";

export async function save(pageId, content, showProgress = true) {
    showProgress && show_modal(_l("Saving page"), _l("progress"));
    try {
        const response = await axios
            .post(`${getAppRoot()}api/pages/${pageId}/revisions`, { content: content })
            .finally(showProgress && hide_modal);
        return response;
    } catch (e) {
        rethrowSimple(e);
    }
}

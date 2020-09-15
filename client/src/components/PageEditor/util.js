import axios from "axios";
import _l from "utils/localization";
import { getAppRoot } from "onload/loadConfig";
import { show_modal, hide_modal } from "layout/modal";
import { Toast } from "ui/toast";
import { errorMessageAsString } from "utils/simple-error";

export const save = (pageId, content) => {
    show_modal(_l("Saving page"), _l("progress"));

    axios
        .post(`${getAppRoot()}api/pages/${pageId}/revisions`, { content: content })
        .finally(hide_modal)
        .catch((error_message) => Toast.error("Failed to save page: " + errorMessageAsString(error_message)));
};

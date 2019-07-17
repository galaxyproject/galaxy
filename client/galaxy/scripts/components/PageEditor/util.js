import $ from "jquery";
import _l from "utils/localization";
import { getAppRoot } from "onload/loadConfig";
import { show_modal, hide_modal } from "layout/modal";

export const save = (pageId, content) => {
    console.log(`content is ${content}`);

    show_modal(_l("Saving page"), _l("progress"));

    // Do save.
    $.ajax({
        url: `${getAppRoot()}page/save`,
        type: "POST",
        data: {
            id: pageId,
            content: content,
            _: "true"
        },
        success: function() {
            hide_modal();
        }
    });
};

import $ from "jquery";
import DataDialog from "components/DataDialog.vue";
import Vue from "vue";
import { getGalaxyInstance } from "app";
import { getAppRoot } from "onload/loadConfig";

export default class Data {
    /**
     * Opens a modal dialog for data selection
     * @param {function} callback - Result function called with selection
     */
    dialog(callback) {
        var instance = Vue.extend(DataDialog);
        var vm = document.createElement("div");
        $("body").append(vm);
        new instance({
            propsData: {
                callback: callback
            }
        }).$mount(vm);
    }

    /**
     * Creates a history dataset by submitting an upload request
     */
    create(options) {
        let Galaxy = getGalaxyInstance();
        let history_panel = Galaxy.currHistoryPanel;
        let history_id = options.history_id;
        if (!history_id && history_panel) {
            history_id = history_panel.model.get("id");
        }
        $.uploadpost({
            url: `${getAppRoot()}api/tools`,
            success: response => {
                if (history_panel) {
                    history_panel.refreshContents();
                }
                if (options.success) {
                    options.success(response);
                }
            },
            error: options.error,
            data: {
                payload: {
                    tool_id: "upload1",
                    history_id: history_id,
                    inputs: JSON.stringify({
                        "files_0|type": "upload_dataset",
                        "files_0|NAME": options.file_name,
                        "files_0|space_to_tab": options.space_to_tab ? "Yes" : null,
                        "files_0|to_posix_lines": options.to_posix_lines ? "Yes" : null,
                        "files_0|dbkey": options.genome || "?",
                        "files_0|file_type": options.extension || "auto",
                        "files_0|url_paste": options.url_paste
                    })
                }
            }
        });
    }
}

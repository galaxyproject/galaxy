import axios from "axios";
import $ from "jquery";
import { getAppRoot } from "onload/loadConfig";
import Vue from "vue";

// This should be moved more centrally (though still hanging off Galaxy for
// external use?), and populated from the store; just using this as a temporary
// interface.
export async function getCurrentGalaxyHistory(galaxy) {
    if (galaxy.currHistoryPanel && galaxy.currHistoryPanel.model.id) {
        // TODO: use central store for this.
        return galaxy.currHistoryPanel.model.id;
    } else {
        // Otherwise manually fetch the current history json and use that id.
        return axios
            .get(`${getAppRoot()}history/current_history_json`)
            .then((response) => {
                return response.data.id;
            })
            .catch((err) => {
                console.error("Error fetching current user history:", err);
                return null;
            });
    }
}

export function mountSelectionDialog(clazz, options) {
    const instance = Vue.extend(clazz);
    const vm = document.createElement("div");
    $("body").append(vm);
    new instance({
        propsData: options,
    }).$mount(vm);
}

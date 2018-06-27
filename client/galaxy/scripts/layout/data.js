import DataDialog from "components/DataDialog.vue";
import Vue from "vue";

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
}

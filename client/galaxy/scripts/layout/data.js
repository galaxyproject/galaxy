import DataDialog from "components/DataDialog.vue";
import Vue from "vue";

export default class Data {
    dialog(callback) {
        var instance = Vue.extend(DataDialog);
        var vm = document.createElement("div");
        $('body').append(vm);
        new instance(({
            propsData: {
                callback: callback
            }
        })).$mount(vm);
    }
}

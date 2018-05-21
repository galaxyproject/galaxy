import DataDialog from "components/DataDialog.vue";
import Vue from "vue";

export default class Data {
    dialog(options) {
        var instance = Vue.extend(DataDialog);
        var vm = document.createElement("div");
        $('body').append(vm);
        new instance().$mount(vm);
    }
}

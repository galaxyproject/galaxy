import Vue from "vue";
import UploadModal from "./UploadModal";
import { initializeUploadDefaults } from "./config";
import store from "../../store";

export function mount(propsData = {}) {
    propsData = initializeUploadDefaults(propsData);
    const instance = Vue.extend(UploadModal);
    const vm = document.createElement("div");
    document.getElementsByTagName("body")[0].appendChild(vm);
    new instance({
        propsData: propsData,
        store,
    }).$mount(vm);
}

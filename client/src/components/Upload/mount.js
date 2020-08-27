import Vue from "vue";
import UploadModal from "./UploadModal";
import { initializeUploadDefaults } from "./config";

export function mount(propsData = {}) {
    propsData = initializeUploadDefaults(propsData);
    const instance = Vue.extend(UploadModal);
    const vm = document.createElement("div");
    document.getElementsByTagName("body")[0].appendChild(vm);
    new instance({
        propsData: propsData,
    }).$mount(vm);
}

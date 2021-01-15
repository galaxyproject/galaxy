import UploadModal from "./UploadModal";
import { initializeUploadDefaults } from "./config";
import { mountVueComponent } from "utils/mountVueComponent";

let instance;

export function mount(options = {}) {
    const propsData = initializeUploadDefaults(options);
    if (!instance) {
        const mounter = mountVueComponent(UploadModal);
        const container = document.createElement("div");
        document.body.appendChild(container);
        instance = mounter(propsData, container);
    } else {
        instance.setProps(propsData);
    }
}

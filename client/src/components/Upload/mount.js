import UploadModal from "./UploadModal";
import { initializeUploadDefaults } from "./config";
import { mountVueComponent } from "utils/mountVueComponent";

export function mount(options = {}) {
    const propsData = initializeUploadDefaults(options);
    const mounter = mountVueComponent(UploadModal);
    const container = document.createElement("div");
    document.body.appendChild(container);
    mounter(propsData, container);
}

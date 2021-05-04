import UploadModal from "./UploadModal";
import { initializeUploadDefaults } from "./config";
import { mountVueComponent } from "utils/mountVueComponent";

export function mountUploadModal(options = {}) {
    const props = initializeUploadDefaults(options);

    // should use events insted of passing in functions
    const { callback, ...propsData } = props;
    if (callback) {
        // internal display characteristic
        propsData.hasCallback = true;
    }

    const mounter = mountVueComponent(UploadModal);
    const container = document.createElement("div");
    document.body.appendChild(container);
    const uploadVm = mounter(propsData, container);

    if (callback) {
        uploadVm.$once("uploadResult", callback);
    }

    return uploadVm;
}

// Global upload dialog instance
let uploadVm = null;

export function openGlobalUploadModal(options) {
    if (!uploadVm) {
        uploadVm = mountUploadModal(options);
    }
    // re-open
    uploadVm.$emit("openUpload", uploadVm);
    return uploadVm;
}

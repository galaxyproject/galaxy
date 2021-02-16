import UploadModal from "./UploadModal";
import { initializeUploadDefaults } from "./config";
import { mountVueComponent } from "utils/mountVueComponent";
import { eventHub } from "components/plugins/eventHub";

// Upload dialog instance
let uploadVm = null;

export function mountUploadModal(options = {}) {
    const propsData = initializeUploadDefaults(options);

    if (!uploadVm) {
        const mounter = mountVueComponent(UploadModal);
        const container = document.createElement("div");
        document.body.appendChild(container);
        uploadVm = mounter(propsData, container);
    } else {
        for (const [propName, v] of Object.entries(propsData)) {
            if (propName in uploadVm.$options.props) {
                uploadVm[propName] = v;
            }
        }
    }
}

export function openUploadModal(options) {
    mountUploadModal(options);
    eventHub.$emit("upload:open");
}

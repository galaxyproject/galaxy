import { ref } from "vue";

let modal = ref(null);

export function setGlobalUploadModal(modalRef) {
    modal = modalRef;
}

export function useGlobalUploadModal() {
    const openGlobalUploadModal = (options) => {
        modal.value?.open(options);
    };

    return { openGlobalUploadModal };
}

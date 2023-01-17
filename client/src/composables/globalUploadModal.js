import { ref } from "vue";

let modal = ref(null);

export function setGlobalUploadModal(modalRef) {
    // eslint-disable-next-line vue/no-ref-as-operand
    modal = modalRef;
}

export function useGlobalUploadModal() {
    const openGlobalUploadModal = (options) => {
        modal.value?.open(options);
    };

    return { openGlobalUploadModal };
}

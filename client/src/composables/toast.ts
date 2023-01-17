import { ref, type Ref } from "vue";

import type Vue from "vue";
import type ToastComponentFile from "@/components/Toast";

export type ToastComponent = Vue & typeof ToastComponentFile.methods;

let toastRef: Ref<ToastComponent | null> = ref(null);

export const setToastComponentRef = (newRef: typeof toastRef) => {
    // eslint-disable-next-line vue/no-ref-as-operand
    toastRef = newRef;
};

/**
 * Direct export to simplify usage in Options Api component.
 * Use 'useToast' for the Composition Api instead.
 */
export const Toast = {
    success(message: string, title = "Success") {
        toastRef.value?.showToast(message, title, "success");
    },

    info(message: string, title = "Info") {
        toastRef.value?.showToast(message, title, "info");
    },

    warning(message: string, title = "Warning") {
        toastRef.value?.showToast(message, title, "warning");
    },

    error(message: string, title = "Error") {
        toastRef.value?.showToast(message, title, "error");
    },
};

export function useToast() {
    return { ...Toast };
}

import { ref } from "vue";

let toastRef = ref(null);

export const setToastComponentRef = (newRef) => {
    toastRef = newRef;
};

/**
 * Direct export to simplify usage in Options Api component.
 * Use 'useToast' for the Composition Api instead.
 */
export const Toast = {
    success(message, title = "Success") {
        toastRef.value.showToast(message, title, "success");
    },

    info(message, title = "Info") {
        toastRef.value.showToast(message, title, "info");
    },

    warning(message, title = "Warning") {
        toastRef.value.showToast(message, title, "warning");
    },

    error(message, title = "Error") {
        toastRef.value.showToast(message, title, "error");
    },
};

export function useToast() {
    return { ...Toast };
}

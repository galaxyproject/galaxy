import { ref } from "vue";

let confirmDialogRef = ref(null);

export const setConfirmDialogComponentRef = (newRef) => {
    // eslint-disable-next-line vue/no-ref-as-operand
    confirmDialogRef = newRef;
};

/**
 * Direct export to simplify usage in Options API component.
 * Use 'useConfirmDialog' for the Composition API instead.
 */
export const ConfirmDialog = {
    /**
     * Displays a simple confirmation message to the user.
     * For additional options see https://bootstrap-vue.org/docs/components/modal#modal-message-boxes.
     * @param {String} message The message to display to the user.
     * @param {Object} options Additional display options to customize the dialog.
     * @returns A promise with `true` if the user confirms the message.
     */
    async confirm(message, options = {}) {
        return confirmDialogRef.value.confirm(message, options);
    },
};

export function useConfirmDialog() {
    return { ...ConfirmDialog };
}

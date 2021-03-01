import { Toast } from "ui/toast";

export const MAX_DESCRIPTION_LENGTH = 40;
export const DEFAULT_PER_PAGE = 15;
export function onError(error) {
    if (typeof error.responseJSON !== "undefined") {
        Toast.error(error.responseJSON.err_msg);
    } else {
        Toast.error("An error occurred during with the last library interaction");
    }
}

import { Toast } from "ui/toast";

export const MAX_DESCRIPTION_LENGTH = 40;
export const DEFAULT_PER_PAGE = 10;
export function onError(error) {
    if (typeof error.responseJSON !== "undefined") {
        Toast.error(error.responseJSON.err_msg);
    } else {
        Toast.error("An error occurred during with the last library interaction");
    }
}

// legacy code
export function extractRoles(role_list) {
    const selected_roles = [];
    role_list.forEach((item) => {
        selected_roles.push({ name: item[0], id: item[1] });
    });

    return selected_roles;
}

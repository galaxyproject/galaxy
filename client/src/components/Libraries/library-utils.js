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

/** This utility function helps to create table fields for title/value pairs.
 * It maps the title in `fieldTitles` to the value of that property from the object `data`.
 * @param {Object} fieldTitles   Contains property/title pairs.
 * @param {Object} data     Contains property/value pairs.
 * @returns An array with name/value pairs with the corresponding title and the actual value
 * of the property contained in `data`.
 */
export function buildFields(fieldTitles, data) {
    return Object.entries(fieldTitles).flatMap(([property, title]) =>
        data[property] ? { name: title, value: data[property] } : []
    );
}

// legacy code
export function extractRoles(role_list) {
    const selected_roles = [];

    if (role_list) {
        role_list.forEach((item) => {
            selected_roles.push({ name: item[0], id: item[1] });
        });
    }

    return selected_roles;
}

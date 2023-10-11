import type { RawLocation } from "vue-router";

const statusMap = new Map([
    ["error", "danger"],
    ["success", "success"],
]);

export function getRedirectOnImportPath(
    response: { id?: string; message?: string; status?: string },
    isRunFormRedirect = false
): RawLocation {
    if (isRunFormRedirect) {
        return { path: "/workflows/run", query: { id: response.id } };
    } else {
        return {
            path: "/workflows/list",
            query: {
                message: response.message ?? "Import Successful",
                status: statusMap.get(response.status ?? "") ?? "success",
            },
        };
    }
}

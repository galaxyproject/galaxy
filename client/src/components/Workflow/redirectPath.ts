import { type RawLocation } from "vue-router";

import { Toast } from "@/composables/toast";

export function getRedirectOnImportPath(
    response: { id?: string; message?: string; status?: string },
    isRunFormRedirect = false
): RawLocation {
    if (isRunFormRedirect) {
        return { path: "/workflows/run", query: { id: response.id } };
    } else {
        if (response.status === "error") {
            Toast.error(response.message ?? "导入失败");
        } else {
            Toast.success(response.message ?? "导入成功");
        }

        return {
            path: "/workflows/list",
        };
    }
}

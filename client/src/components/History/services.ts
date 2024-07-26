import axios from "axios";

import { type Input, permissionInputParts } from "@/composables/datasetPermissions";
import { withPrefix } from "@/utils/redirect";

export function getPermissionsUrl(historyId: string) {
    return `/history/permissions?id=${historyId}`;
}

export interface PermissionsResponse {
    inputs: Input[];
}

export function getPermissions(historyId: string) {
    const permissionsUrl = getPermissionsUrl(historyId);
    return axios.get(withPrefix(permissionsUrl));
}

export function setPermissions(historyId: string, formContents: object) {
    const permissionsUrl = getPermissionsUrl(historyId);
    return axios.put(withPrefix(permissionsUrl), formContents);
}

export function makePrivate(historyId: string, permissionResponse: PermissionsResponse) {
    const { manageInput } = permissionInputParts(permissionResponse.inputs);
    const managePermissionValue: number = manageInput.value[0] as number;
    const access = [managePermissionValue];
    const formValue = {
        DATASET_MANAGE_PERMISSIONS: [managePermissionValue],
        DATASET_ACCESS: access,
    };
    return setPermissions(historyId, formValue);
}

export async function isHistoryPrivate(permissionResponse: PermissionsResponse) {
    const { accessInput } = permissionInputParts(permissionResponse.inputs);
    return accessInput.value.length >= 1;
}

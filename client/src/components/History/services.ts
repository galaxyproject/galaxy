import axios from "axios";

import { fetcher } from "@/api/schema";
import { type Input, permissionInputParts } from "@/composables/datasetPermissions";
import type Filtering from "@/utils/filtering";
import { withPrefix } from "@/utils/redirect";

const publishedHistoriesFetcher = fetcher.path("/api/histories/published").method("get").create();
export async function getPublishedHistories(
    limit: number,
    offset: number | null,
    sortBy: string,
    sortDesc: boolean,
    filterText: string,
    filters: Filtering<unknown>
) {
    const view = "summary";
    const keys = "username,username_and_slug";
    const queryDict = filters.getQueryDict(filterText);
    const order = sortBy ? `${sortBy}${sortDesc ? "-dsc" : "-asc"}` : undefined;

    const { data } = await publishedHistoriesFetcher({
        limit,
        offset,
        order,
        view,
        keys,
        q: Object.keys(queryDict),
        qv: Object.entries(queryDict).map(([__, v]) => v as string),
    });

    return data;
}

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

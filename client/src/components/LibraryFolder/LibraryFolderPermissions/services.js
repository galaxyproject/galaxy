import axios from "axios";
import { rethrowSimple } from "utils/simple-error";
import { getAppRoot } from "onload/loadConfig";

export class Services {
    constructor(options = {}) {
        this.root = options.root || getAppRoot();
    }

    async getFolderPermissions(id) {
        const url = `${this.root}api/folders/${id}/permissions?scope=current`;
        try {
            const response = await axios.get(url);
            return response.data;
        } catch (e) {
            rethrowSimple(e);
        }
    }
    async getDatasetPermissions(id) {
        const url = `${this.root}api/libraries/datasets/${id}/permissions?scope=current`;
        try {
            const response = await axios.get(url);
            return response.data;
        } catch (e) {
            rethrowSimple(e);
        }
    }
    async getDataset(id) {
        const url = `${this.root}api/libraries/datasets/${id}`;
        try {
            const response = await axios.get(url);
            return response.data;
        } catch (e) {
            rethrowSimple(e);
        }
    }
    async getFolder(id) {
        const url = `${this.root}api/folders/${id}`;
        try {
            const response = await axios.get(url);
            return response.data;
        } catch (e) {
            rethrowSimple(e);
        }
    }
    async getSelectOptions(apiRootUrl, id, is_library_access, page, page_limit, searchQuery) {
        searchQuery = searchQuery ? `&q=${searchQuery}` : "";
        const url = `${apiRootUrl}/${id}/permissions?scope=available&is_library_access=${is_library_access}&page_limit=${page_limit}&page=${page}${searchQuery}`;
        try {
            const response = await axios.get(url);
            return response.data;
        } catch (e) {
            rethrowSimple(e);
        }
    }

    async setPermissions(apiRootUrl, id, new_roles_ids, onSuccess, onError) {
        var formData = new FormData();
        new_roles_ids.forEach((permissionType) => {
            Object.keys(permissionType).map(function (k) {
                const ids = permissionType[k].map((a) => a.id);
                formData.append(k, ids);
            });
        });

        axios({
            method: "post",
            url: `${apiRootUrl}/${id}/permissions?action=set_permissions`,
            data: formData,
            headers: { "Content-Type": "multipart/form-data" },
        })
            .then(function (response) {
                onSuccess(response);
            })
            .catch((response) => {
                onError(response);
            });
    }
}

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
    async toggleDatasetPrivacy(id, isMakePrivate, onSuccess, onError) {
        await axios
            .post(
                `${getAppRoot()}api/libraries/datasets/${id}/permissions?action=${
                    isMakePrivate ? "make_private" : "remove_restrictions"
                }`
            )
            .then((fetched_permissions) => {
                onSuccess(fetched_permissions.data);
            })
            .catch((response) => {
                onError(response);
            });
    }
}

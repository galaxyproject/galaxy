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
    async getFolder(id) {
        const url = `${this.root}api/folders/${id}`;
        try {
            const response = await axios.get(url);
            return response.data;
        } catch (e) {
            rethrowSimple(e);
        }
    }
    async getSelectOptions(id, is_library_access, page, page_limit, query) {
        const url = `${this.root}api/folders/${id}/permissions?scope=available&is_library_access=${is_library_access}&page_limit=${page_limit}&page=${page}`;
        try {
            const response = await axios.get(url);
            return response.data;
        } catch (e) {
            rethrowSimple(e);
        }
    }
    async setPermisions(access_ids, add_ids, manage_ids, modify_ids, onSuccess, onError) {
        var formData = new FormData();
        formData.append("add_ids[]", access_ids);
        formData.append("manage_ids[]", manage_ids);
        formData.append("modify_ids[]", modify_ids);

        axios({
            method: "post",
            url: "`${getAppRoot()}api/libraries/${self.id}/permissions?action=set_permissions`",
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

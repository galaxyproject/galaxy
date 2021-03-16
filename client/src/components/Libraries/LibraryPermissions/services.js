import axios from "axios";
import { rethrowSimple } from "utils/simple-error";
import { getAppRoot } from "onload/loadConfig";

export class Services {
    constructor(options = {}) {
        this.root = options.root || getAppRoot();
    }

    async getLibraryPermissions(id) {
        const url = `${this.root}api/libraries/${id}/permissions?scope=current`;
        try {
            const response = await axios.get(url);
            return response.data;
        } catch (e) {
            rethrowSimple(e);
        }
    }
    async getLibrary(id) {
        const url = `${this.root}api/libraries/${id}`;
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
}

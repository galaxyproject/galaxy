import axios from "axios";
import { rethrowSimple } from "utils/simple-error";
import { getAppRoot } from "onload/loadConfig";

export class Services {
    constructor(options = {}) {
        this.root = options.root || getAppRoot();
    }

    async getCompositeDatasetContentFiles(id) {
        const url = `${this.root}api/histories/${id}/contents/${id}/extra_files`;
        try {
            const response = await axios.get(url);
            return response.data;
        } catch (e) {
            rethrowSimple(e);
        }
    }
    async getCompositeDatasetDirectory(url) {
        try {
            const response = await axios.get(url);
            return response.data;
        } catch (e) {
            rethrowSimple(e);
        }
    }
    async getCompositeDatasetInfo(id) {
        const url = `${this.root}api/histories/${id}/contents/${id}`;
        try {
            const response = await axios.get(url);
            return response.data;
        } catch (e) {
            rethrowSimple(e);
        }
    }

}

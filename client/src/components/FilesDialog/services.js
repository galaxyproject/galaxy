import axios from "axios";
import { rethrowSimple } from "utils/simple-error";
import { getAppRoot } from "onload/loadConfig";

export class Services {
    constructor(options = {}) {
        this.root = options.root || getAppRoot();
    }

    async getFileSources() {
        const url = `${this.root}api/remote_files/plugins`;
        try {
            const response = await axios.get(url);
            const fileSources = response.data;
            return fileSources;
        } catch (e) {
            rethrowSimple(e);
        }
    }

    async list(uri, isRecursive = false) {
        const url = `${this.root}api/remote_files?target=${uri}${isRecursive ? "&recursive=true" : ""}`;
        try {
            const response = await axios.get(url);
            return response.data;
        } catch (e) {
            rethrowSimple(e);
        }
    }
}

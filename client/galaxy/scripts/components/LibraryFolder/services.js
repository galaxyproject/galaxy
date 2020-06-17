import axios from "axios";
import {rethrowSimple} from "utils/simple-error";
import {getAppRoot} from "onload/loadConfig";

export class Services {
    constructor(options = {}) {
        this.root = options.root || getAppRoot();
    }

    async getFolderContents(id) {
        const url = `${this.root}api/folders/${id}/contents`;
        try {
            const response = await axios.get(url);
            return response.data;
        } catch (e) {
            rethrowSimple(e);
        }
    }
}

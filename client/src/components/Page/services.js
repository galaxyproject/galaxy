import axios from "axios";
import { rethrowSimple } from "utils/simple-error";
import { getAppRoot } from "onload/loadConfig";

/** Page request helper **/
export class Services {
    constructor(options = {}) {
        this.root = options.root || getAppRoot();
    }

    async deletePage(id) {
        const url = `${this.root}api/pages/${id}`;
        try {
            const response = await axios.delete(url);
            return response.data;
        } catch (e) {
            rethrowSimple(e);
        }
    }
}

import axios from "axios";
import { rethrowSimple } from "utils/simple-error";
import { getAppRoot } from "onload/loadConfig";

export class Services {
    constructor(options = {}) {
        this.root = options.root || getAppRoot();
    }

    async decode(id) {
        const url = `${this.root}api/security/decode/${id}`;
        try {
            return await axios.get(url);
        } catch (e) {
            rethrowSimple(e);
        }
    }
}

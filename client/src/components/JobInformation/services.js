import axios from "axios";
import { getAppRoot } from "onload/loadConfig";
import { rethrowSimple } from "utils/simple-error";

export class Services {
    constructor(options = {}) {
        this.root = options.root || getAppRoot();
    }

    async decode(id) {
        const url = `${this.root}api/configuration/decode/${id}`;
        try {
            return await axios.get(url);
        } catch (e) {
            rethrowSimple(e);
        }
    }
}

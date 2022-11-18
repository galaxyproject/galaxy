import axios from "axios";
import { rethrowSimple } from "utils/simple-error";
import { getAppRoot } from "onload/loadConfig";

export class Services {
    constructor(options = {}) {
        this.root = options.root || getAppRoot();
    }

    async stopInteractiveTool(id) {
        const url = `${this.root}api/entry_points/${id}`;
        const response = await axios.delete(url);
        return response.data;
    }
    catch(e) {
        rethrowSimple(e);
    }
}

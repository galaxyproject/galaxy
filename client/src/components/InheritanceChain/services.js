import axios from "axios";
import { getAppRoot } from "onload/loadConfig";
import { rethrowSimple } from "utils/simple-error";

export class Services {
    constructor(options = {}) {
        this.root = options.root || getAppRoot();
    }

    async getInheritanceChain(datasetId) {
        const url = `${this.root}api/datasets/${datasetId}/inheritance_chain`;
        try {
            const response = await axios.get(url);
            return response.data;
        } catch (e) {
            rethrowSimple(e);
        }
    }

    catch(e) {
        rethrowSimple(e);
    }
}

import axios from "axios";
import { rethrowSimple } from "utils/simple-error";
import { getAppRoot } from "onload/loadConfig";

/** Workflow data request helper **/
export class Services {
    constructor(options = {}) {
        this.root = options.root || getAppRoot();
    }
}

export async function getVersions() {
    const url = `${getAppRoot()}api/workflows/${self.id}/versions`;
    try {
        const response = await axios.get(url);
        return response.data;
    } catch (e) {
        rethrowSimple(e);
    }
}

export async function getDatatypes() {
    try {
        const datatypesRequest = await axios.get(`${getAppRoot()}api/datatypes`);
        const datatypes = datatypesRequest.data;
        const mappingRequest = await axios.get(`${getAppRoot()}api/datatypes/mapping`);
        const datatypes_mapping = mappingRequest.data;
        return { datatypes, datatypes_mapping };
    } catch (e) {
        rethrowSimple(e);
    }
}

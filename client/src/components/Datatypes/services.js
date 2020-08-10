import axios from "axios";
import { rethrowSimple } from "utils/simple-error";
import { getAppRoot } from "onload/loadConfig";

export async function getDatatypes() {
    try {
        const request = await axios.get(`${getAppRoot()}api/datatypes/types_and_mapping`);
        return request.data;
    } catch (e) {
        rethrowSimple(e);
    }
}

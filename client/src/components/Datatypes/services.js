import axios from "axios";
import { rethrowSimple } from "utils/simple-error";
import { getAppRoot } from "onload/loadConfig";

export async function getDatatypes(upload_only = true) {
    try {
        const request = await axios.get(`${getAppRoot()}api/datatypes/types_and_mapping`, {
            params: {
                upload_only: upload_only,
            },
        });
        return request.data;
    } catch (e) {
        rethrowSimple(e);
    }
}

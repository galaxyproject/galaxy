import axios from "axios";
import { prependPath } from "utils/redirect";

export async function getConfig() {
    const url = prependPath("/api/configuration");
    const response = await axios.get(url);
    if (response.status != 200) {
        throw new Error(response);
    }
    return response.data;
}

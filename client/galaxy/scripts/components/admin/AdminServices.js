import { getAppRoot } from "onload/loadConfig";
import axios from "axios";

export function getErrorStack() {
    let url = `${getAppRoot()}api/tools/error_stack`;
    return axios.get(url);
}

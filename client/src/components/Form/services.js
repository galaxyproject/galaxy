import axios from "axios";
import { rethrowSimple } from "utils/simple-error";
import { safePath } from "utils/redirect";

export async function submitData(url, payload) {
    try {
        const { data } = await axios.put(safePath(url), payload);
        return data;
    } catch (e) {
        rethrowSimple(e);
    }
}

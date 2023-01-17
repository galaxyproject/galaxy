import axios from "axios";
import { rethrowSimple } from "utils/simple-error";
import { withPrefix } from "utils/redirect";

export async function submitData(url, payload) {
    try {
        const { data } = await axios.put(withPrefix(url), payload);
        return data;
    } catch (e) {
        rethrowSimple(e);
    }
}

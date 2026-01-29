import axios from "axios";
import { withPrefix } from "utils/redirect";
import { rethrowSimple } from "utils/simple-error";

export async function submitData(url, payload) {
    try {
        const { data } = await axios.put(withPrefix(url), payload);
        return data;
    } catch (e) {
        rethrowSimple(e);
    }
}

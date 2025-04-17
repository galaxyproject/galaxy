import axios from "axios";
import { withPrefix } from "@/utils/redirect";
import { rethrowSimple } from "@/utils/simple-error";

export async function fetchPlugins() {
    try {
        const { data } = await axios.get(withPrefix(`/api/plugins`));
        return data;
    } catch (error) {
        rethrowSimple(error);
    }
}

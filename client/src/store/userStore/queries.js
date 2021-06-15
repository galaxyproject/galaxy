import axios from "axios";
import { prependPath } from "utils/redirect";

export async function getCurrentUser() {
    const url = prependPath("/api/users/current");
    const response = await axios.get(url);
    if (response.status != 200) {
        throw new Error(response);
    }
    return response.data;
}

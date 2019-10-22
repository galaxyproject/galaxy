import axios from "axios";
import { getAppRoot } from "onload/loadConfig";

export async function getCurrentUser() {
    const root = getAppRoot();
    const url = `${root}api/users/current`;
    const response = await axios.get(url);
    if (response.status != 200) {
        throw new Error(response);
    }
    return response.data;
}

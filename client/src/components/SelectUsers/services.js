import axios from "axios";
import { rethrowSimple } from "utils/simple-error";
import { getAppRoot } from "onload/loadConfig";

export class Services {
    constructor(options = {}) {
        this.root = options.root || getAppRoot();
    }

    async getUsers(searchValue) {
        const url = `${this.root}api/users?f_any=${searchValue}`;
        try {
            const response = await axios.get(url);
            return response.data;
        } catch (e) {
            rethrowSimple(e);
        }
    }

    async saveSharingPreferences(values) {
        const url = `${this.root}history/share`;
        const formData = new FormData();
        formData.append(
            "email",
            values.map(({ email }) => email)
        );

        try {
            const response = await axios.post(url);
            return response.data;
        } catch (e) {
            rethrowSimple(e);
        }
    }
}

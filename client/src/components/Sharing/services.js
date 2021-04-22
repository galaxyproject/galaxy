import axios from "axios";
import { rethrowSimple } from "utils/simple-error";
import { getAppRoot } from "onload/loadConfig";

export class Services {
    constructor(options = {}) {
        this.root = options.root || getAppRoot();
    }

    async getUsers(searchValue) {
        const url = `${this.root}api/users?f_email=${searchValue}`;
        try {
            const response = await axios.get(url);
            return response.data;
        } catch (e) {
            rethrowSimple(e);
        }
    }

    async saveSharingPreferences(pluralName, id, action, user_id) {
        console.log(`${this.root}`);
        console.log(`${this.root}`);
        console.log(`${this.root}`);
        console.log(`${this.root}`);
        console.log(`${this.root}`);
        const url = `${this.root}api/${pluralName}/${id}/sharing`;
        const data = {
            action: action,
            user_ids: [user_id],
        };
        try {
            const response = await axios.post(url, data);
            return response.data;
        } catch (e) {
            rethrowSimple(e);
        }
    }
}

import { getAppRoot } from "@/onload/loadConfig";
import _l from "@/utils/localization";

const CURRENT_ID_STR = "current";

class User {
    constructor(data = {}) {
        this.defaults = {
            id: null,
            username: `(${_l("anonymous user")})`,
            email: "",
            total_disk_usage: 0,
            nice_total_disk_usage: "",
            quota_percent: null,
            is_admin: false,
            preferences: {},
        };
        this.attributes = { ...this.defaults, ...data };
    }

    urlRoot() {
        return `${getAppRoot()}api/users`;
    }

    get(attr) {
        return this.attributes[attr];
    }

    set(attr, value) {
        this.attributes[attr] = value;
    }

    get id() {
        return this.get("id");
    }

    isAnonymous() {
        return !this.get("email");
    }

    isAdmin() {
        return this.get("is_admin");
    }

    async loadFromApi(idOrCurrent = CURRENT_ID_STR) {
        const url = `${this.urlRoot()}/${idOrCurrent}`;
        try {
            const response = await fetch(url, { credentials: "same-origin" });
            const data = await response.json();
            this.attributes = { ...this.defaults, ...data };
            if (!this.attributes.preferences) {
                this.attributes.preferences = {};
            }
        } catch (error) {
            console.error(error);
        }
    }

    clearSessionStorage() {
        //TODO: store these under the user key so we don't have to do this
        for (const key in sessionStorage) {
            if (key.startsWith("history:") || key === "history-panel") {
                sessionStorage.removeItem(key);
            }
        }
    }

    toString() {
        const userInfo = [this.get("username")];
        if (this.get("id")) {
            userInfo.unshift(this.get("id"));
            userInfo.push(this.get("email"));
        }
        return `User(${userInfo.join(":")})`;
    }
}

export default { User };

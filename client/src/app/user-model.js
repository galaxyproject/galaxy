import { getAppRoot } from "onload/loadConfig";
import _l from "utils/localization";

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

    updatePreferences(name, new_value) {
        const prefs = { ...(this.get("preferences") || {}) };
        prefs[name] = JSON.stringify(new_value);
        this.set("preferences", prefs);
    }

    getFavorites() {
        const prefs = this.get("preferences") || {};
        if (prefs.favorites) {
            return JSON.parse(prefs.favorites);
        } else {
            return { tools: [] };
        }
    }

    updateFavorites(object_type, new_favorites) {
        const favorites = this.getFavorites();
        favorites[object_type] = new_favorites[object_type];
        this.updatePreferences("favorites", favorites);
    }

    async loadFromApi(idOrCurrent = CURRENT_ID_STR, options = {}) {
        const url =
            idOrCurrent === CURRENT_ID_STR ? `${this.urlRoot()}/${CURRENT_ID_STR}` : `${this.urlRoot()}/${idOrCurrent}`;
        try {
            const response = await fetch(url, { credentials: "same-origin" });
            const data = await response.json();
            this.attributes = { ...this.defaults, ...data };
            if (!this.attributes.preferences) {
                this.attributes.preferences = {};
            }
            if (options.success) {
                options.success(this, data);
            }
        } catch (error) {
            if (options.error) {
                options.error(this, error);
            } else {
                console.error(error);
            }
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

    static getCurrentUserFromApi(options) {
        const currentUser = new User();
        currentUser.loadFromApi(CURRENT_ID_STR, options);
        return currentUser;
    }
}

export default { User };

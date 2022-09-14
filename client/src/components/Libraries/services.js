import axios from "axios";
import { rethrowSimple } from "utils/simple-error";
import { getAppRoot } from "onload/loadConfig";

export class Services {
    constructor(options = {}) {
        this.root = options.root || getAppRoot();
    }

    async getLibraries(includeDeleted = false) {
        const url = `${this.root}api/libraries?deleted=${includeDeleted}`;
        try {
            const response = await axios.get(url);
            return response.data;
        } catch (e) {
            rethrowSimple(e);
        }
    }
    async saveChanges(lib, onSucess, onError) {
        const url = `${this.root}api/libraries/${lib.id}`;
        try {
            const response = axios
                .patch(url, lib)
                .then((response) => {
                    onSucess(response.data);
                })
                .catch((error) => {
                    onError(error);
                });
            return response.data;
        } catch (e) {
            rethrowSimple(e);
        }
    }
    async deleteLibrary(lib, onSucess, onError, isUndelete = false) {
        const url = `${this.root}api/libraries/${lib.id}${isUndelete ? "?undelete=true" : ""}`;
        try {
            const response = axios
                .delete(url, lib)
                .then((response) => {
                    onSucess(response.data);
                })
                .catch((error) => {
                    onError(error);
                });
            return response.data;
        } catch (e) {
            rethrowSimple(e);
        }
    }
    async createNewLibrary(name, description, synopsis, onSucess, onError) {
        const url = `${this.root}api/libraries`;
        try {
            const response = axios
                .post(url, {
                    name: name,
                    description: description,
                    synopsis: synopsis,
                })
                .then((response) => {
                    onSucess(response.data);
                })
                .catch((error) => {
                    onError(error);
                });
            return response.data;
        } catch (e) {
            rethrowSimple(e);
        }
    }
}

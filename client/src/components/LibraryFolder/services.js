import axios from "axios";
import { rethrowSimple } from "utils/simple-error";
import { getAppRoot } from "onload/loadConfig";

export class Services {
    constructor(options = {}) {
        this.root = options.root || getAppRoot();
    }

    async getFolderContents(id, include_deleted, limit, offset, search_text = false) {
        search_text = search_text ? `&search_text=${encodeURI(search_text)}` : "";
        const url = `${this.root}api/folders/${id}/contents?include_deleted=${include_deleted}&limit=${limit}&offset=${offset}${search_text}`;
        try {
            const response = await axios.get(url);
            return response.data;
        } catch (e) {
            rethrowSimple(e);
        }
    }

    updateFolder(item, onSucess, onError) {
        const url = `${this.root}api/folders/${item.id}`;
        try {
            const response = axios
                .patch(url, item)
                .then(() => {
                    onSucess();
                })
                .catch((error) => {
                    onError(error);
                });
            return response.data;
        } catch (e) {
            rethrowSimple(e);
        }
    }
    newFolder(folder, onSucess, onError) {
        const url = `${this.root}api/folders/${folder.parent_id}`;
        try {
            const response = axios
                .post(url, {
                    name: folder.name,
                    description: folder.description,
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
    undeleteFolder(folder, onSucess, onError) {
        const url = `${this.root}api/folders/${folder.id}?undelete=true`;
        try {
            const response = axios
                .delete(url)
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
    undeleteDataset(dataset, onSucess, onError) {
        const url = `${this.root}api/libraries/datasets/${dataset.id}?undelete=true`;
        try {
            const response = axios
                .delete(url)
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

import axios from "axios";
import { getAppRoot } from "onload/loadConfig";
import { rethrowSimple } from "utils/simple-error";

export class Services {
    constructor(options = {}) {
        this.root = options.root || getAppRoot();
    }

    async getFolderContents(id, include_deleted, limit, offset, search_text = false) {
        const url = `${
            this.root
        }api/folders/${id}/contents?include_deleted=${include_deleted}&limit=${limit}&offset=${offset}${this.getSearchQuery(
            search_text
        )}`;
        try {
            const response = await axios.get(url);
            return response.data;
        } catch (e) {
            rethrowSimple(e);
        }
    }

    async getFilteredFolderContents(id, excluded, search_text) {
        const contents = await axios.get(`${this.root}api/folders/${id}/contents?${this.getSearchQuery(search_text)}`);
        return contents.data.folder_contents.filter((item) => {
            return !excluded.some((exc) => exc.id === item.id);
        });
    }

    getSearchQuery(search_text) {
        return search_text ? `&search_text=${encodeURI(search_text.trim())}` : "";
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
    async getDataset(datasetID, onError) {
        const url = `${this.root}api/libraries/datasets/${datasetID}`;
        try {
            const response = await axios.get(url).catch((error) => {
                onError(error);
            });
            return response.data;
        } catch (e) {
            rethrowSimple(e);
        }
    }
    async updateDataset(datasetID, data, onSucess, onError) {
        const url = `${this.root}api/libraries/datasets/${datasetID}`;
        try {
            await axios
                .patch(url, data)
                .then((response) => onSucess(response.data))
                .catch((error) => {
                    onError(error.err_msg);
                });
        } catch (e) {
            rethrowSimple(e);
        }
    }
}

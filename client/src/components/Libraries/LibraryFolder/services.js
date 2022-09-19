import axios from "axios";
import { getAppRoot } from "onload/loadConfig";
import { rethrowSimple } from "utils/simple-error";

export class Services {
    constructor(options = {}) {
        this.root = options.root || getAppRoot();
    }

    async getFolderContents(folderId, includeDeleted, sortBy, sortDesc, limit, offset, searchText) {
        const url = `${this.root}api/folders/${folderId}/contents`;
        const config = {
            params: {
                include_deleted: includeDeleted,
                sort_by: sortBy,
                sort_desc: sortDesc,
                limit,
                offset,
            },
        };
        searchText = searchText.trim();
        if (searchText) {
            config.params.search_text = searchText;
        }
        try {
            const response = await axios.get(url, config);
            return response.data;
        } catch (e) {
            rethrowSimple(e);
        }
    }

    async getFilteredFolderContents(id, excluded, searchText) {
        const contents = await axios.get(`${this.root}api/folders/${id}/contents?${this.getSearchQuery(searchText)}`);
        return contents.data.folder_contents.filter((item) => {
            return !excluded.some((exc) => exc.id === item.id);
        });
    }

    getSearchQuery(searchText) {
        return searchText ? `&search_text=${encodeURI(searchText.trim())}` : "";
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

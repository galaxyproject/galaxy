import axios from "axios";

/** Datasets request helper **/
export class Services {
    constructor(options = {}) {
        this.root = options.root;
    }

    async getDatasets(options = {}) {
        let params = "";
        if (options.sortBy) {
            const sortPrefix = options.sortDesc ? "-dsc" : "-asc";
            params += `order=${options.sortBy}${sortPrefix}&`;
        }
        if (options.limit) {
            params += `limit=${options.limit}&`;
        }
        if (options.offset) {
            params += `offset=${options.offset}&`;
        }
        if (options.query) {
            params += `q=name-contains&qv=${options.query}&`;
        }
        const url = `${this.root}api/datasets?${params}`;
        try {
            const response = await axios.get(url);
            return response.data;
        } catch (e) {
            this._errorMessage(e);
        }
    }

    async copyDataset(dataset_id, history_id) {
        const url = `${this.root}api/histories/${history_id}/contents`;
        try {
            const response = await axios.post(url, {
                type: "dataset",
                source: "hda",
                content: dataset_id
            });
            return response.data;
        } catch (e) {
            this._errorMessage(e);
        }
    }

    async setHistory(id) {
        const url = `${this.root}history/set_as_current?id=${id}`;
        try {
            const response = await axios.get(url);
            return response.data;
        } catch (e) {
            this._errorMessage(e);
        }
    }

    _errorMessage(e) {
        let message = "Request failed.";
        if (e.response) {
            message = e.response.data.err_msg || `${e.response.statusText} (${e.response.status})`;
        }
        throw message;
    }
}

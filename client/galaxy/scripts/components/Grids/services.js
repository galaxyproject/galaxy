import axios from "axios";

/** Datasets request helper **/
export class Services {
    constructor(options = {}) {
        this.root = options.root;
    }

    async getDatasets(query, sortBy, sortDesc) {
        let sortAsc = "";
        if (!sortDesc) {
            sortAsc = "-asc";
        }
        let params = `order=${sortBy}${sortAsc}`;
        if (query) {
            params += `&q=name-contains&qv=${query}`;
        }
        const url = `${this.root}api/datasets?${params}`;
        console.log(url);
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

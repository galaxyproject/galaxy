import axios from "axios";
import { prependPath } from "utils/redirect";
import { rethrowSimple } from "utils/simple-error";

export class Services {
    async getPublishedHistories(options = {}) {
        let params = "view=summary&keys=username,username_and_slug&";

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

        const url = `api/histories/published?${params}`;

        try {
            const { data } = await axios.get(prependPath(url));
            return data;
        } catch (e) {
            rethrowSimple(e);
        }
    }
}

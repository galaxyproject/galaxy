import axios from "axios";
import { getAppRoot } from "onload/loadConfig";
import { SingleQueryProvider } from "components/providers/SingleQueryProvider";
import { rethrowSimple } from "utils/simple-error";

async function urlData({ url }) {
    console.log(url);
    try {
        const { data } = await axios.get(`${getAppRoot()}${url}`);
        console.log(data);
        return data;
    } catch (e) {
        rethrowSimple(e);
    }
}

export const UrlDataProvider = SingleQueryProvider(urlData);

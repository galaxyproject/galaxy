import axios from "axios";
import { SingleQueryProvider } from "components/providers/SingleQueryProvider";
import { getAppRoot } from "onload/loadConfig";
import { rethrowSimple } from "utils/simple-error";
import { QuotaUsage } from "./model";

// TODO: replace this with the proper provider and API call after
// https://github.com/galaxyproject/galaxy/pull/10977 is available

/**
 * Fetches the disk usage by the user across all ObjectStores.
 * @returns {Array<QuotaUsage>}
 */
async function fetchQuotaUsage() {
    const url = `${getAppRoot()}api/users/current`;
    try {
        const { data } = await axios.get(url);
        return [new QuotaUsage(data)];
    } catch (e) {
        rethrowSimple(e);
    }
}

export const QuotaUsageProvider = SingleQueryProvider(fetchQuotaUsage);

import axios from "axios";
import { SingleQueryProvider } from "components/providers/SingleQueryProvider";
import { getAppRoot } from "onload/loadConfig";
import { rethrowSimple } from "utils/simple-error";
import { QuotaUsage } from "./model";

/**
 * Fetches the disk usage corresponding to one quota source label -
 * or the default quota sources if the supplied label is null.
 * @returns {<QuotaUsage>}
 */
async function fetchQuotaSourceUsage({ quotaSourceLabel = null }) {
    if (quotaSourceLabel == null) {
        quotaSourceLabel = "__null__";
    }
    const url = `${getAppRoot()}api/users/current/usage/${quotaSourceLabel}`;
    try {
        const { data } = await axios.get(url);
        return new QuotaUsage(data);
    } catch (e) {
        rethrowSimple(e);
    }
}

export const QuotaSourceUsageProvider = SingleQueryProvider(fetchQuotaSourceUsage);

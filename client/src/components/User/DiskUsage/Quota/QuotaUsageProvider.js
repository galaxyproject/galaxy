import { SingleQueryProvider } from "components/providers/SingleQueryProvider";

import { fetchCurrentUserQuotaSourceUsage } from "@/api/users";

/**
 * Fetches the disk usage corresponding to one quota source label -
 * or the default quota sources if the supplied label is null.
 */
async function fetchQuotaSourceUsage({ quotaSourceLabel = null }) {
    return fetchCurrentUserQuotaSourceUsage(quotaSourceLabel);
}

// TODO: replace provider pattern with composable
export const QuotaSourceUsageProvider = SingleQueryProvider(fetchQuotaSourceUsage);

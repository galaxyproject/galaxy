import { fetchQuotaUsages } from "@/api/users";

import { QuotaUsage, UserQuotaUsageData } from "./model/index";

export async function fetch() {
    const { data } = await fetchQuotaUsages({ user_id: "current" });
    return data.map((u: UserQuotaUsageData) => new QuotaUsage(u));
}

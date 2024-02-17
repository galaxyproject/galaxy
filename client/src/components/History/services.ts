import { fetcher } from "@/api/schema";
import type Filtering from "@/utils/filtering";

const publishedHistoriesFetcher = fetcher.path("/api/histories/published").method("get").create();
export async function getPublishedHistories(
    limit: number,
    offset: number | null,
    sortBy: string,
    sortDesc: boolean,
    filterText: string,
    filters: Filtering<unknown>
) {
    const view = "summary";
    const keys = "username,username_and_slug";
    const queryDict = filters.getQueryDict(filterText);
    const order = sortBy ? `${sortBy}${sortDesc ? "-dsc" : "-asc"}` : undefined;

    const { data } = await publishedHistoriesFetcher({
        limit,
        offset,
        order,
        view,
        keys,
        q: Object.keys(queryDict),
        qv: Object.entries(queryDict).map(([__, v]) => v as string),
    });

    return data;
}

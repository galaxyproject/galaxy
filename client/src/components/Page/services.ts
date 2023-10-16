import type { FetchArgType } from "openapi-typescript-fetch";

import { fetcher } from "@/api/schema";

/** Page request helper **/
const _deletePage = fetcher.path("/api/pages/{id}").method("delete").create();
type PageDeleteArgs = FetchArgType<typeof _deletePage>;
export async function deletePage(itemId: PageDeleteArgs["id"]) {
    const { data } = await _deletePage({
        id: itemId,
    });
    return data;
}

import type { FetchArgType } from "openapi-typescript-fetch";
import { fetcher } from "@/schema";

/** Page request helper **/
const _deletePage = fetcher.path("/api/pages/{id}").method("delete").create();
type PageDeleteArgs = FetchArgType<typeof _deletePage>;
export async function deletePage(itemId: PageDeleteArgs["id"]) {
    const { data } = await _deletePage({
        id: itemId,
    });
    return data;
}

const _updateTags = fetcher.path("/api/tags").method("put").create();
type UpdateTagsArgs = FetchArgType<typeof _updateTags>;
export async function updateTags(
    itemId: UpdateTagsArgs["item_id"],
    itemClass: UpdateTagsArgs["item_class"],
    itemTags: UpdateTagsArgs["item_tags"]
) {
    const { data } = await _updateTags({
        item_id: itemId,
        item_class: itemClass,
        item_tags: itemTags,
    });
    return data;
}

import { components, fetcher } from "@/api/schema";

type TaggableItemClass = components["schemas"]["TaggableItemClass"];

const putItemTags = fetcher.path("/api/tags").method("put").create();

export async function updateTags(itemId: string, itemClass: TaggableItemClass, itemTags?: string[]): Promise<void> {
    await putItemTags({
        item_id: itemId,
        item_class: itemClass,
        item_tags: itemTags,
    });
}

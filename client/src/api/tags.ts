import { client, type components } from "@/api/schema";
import { rethrowSimple } from "@/utils/simple-error";

type TaggableItemClass = components["schemas"]["TaggableItemClass"];

export async function updateTags(itemId: string, itemClass: TaggableItemClass, itemTags?: string[]): Promise<void> {
    const { error } = await client.PUT("/api/tags", {
        body: {
            item_id: itemId,
            item_class: itemClass,
            item_tags: itemTags,
        },
    });

    if (error) {
        rethrowSimple(error);
    }
}

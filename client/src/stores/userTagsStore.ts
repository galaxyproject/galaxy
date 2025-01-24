import { until } from "@vueuse/core";
import Dexie from "dexie";
import { defineStore, storeToRefs } from "pinia";
import { computed, ref, watch } from "vue";

import { useHashedUserId } from "@/composables/hashedUserId";
import { assertDefined, ensureDefined } from "@/utils/assertions";

import { useUserStore } from "./userStore";

interface StoredTag {
    id?: number;
    tag: string;
    userHash: string;
    lastUsed: number;
}

class UserTagStoreDatabase extends Dexie {
    tags!: Dexie.Table<StoredTag, number>;

    constructor() {
        super("userTagStoreDatabase");
        this.version(2).stores({ tags: "++id, userHash, lastUsed, tag" });
    }
}

const maxDbEntriesPerUser = 10000;

export function normalizeTag(tag: string) {
    return tag.replace(/^#/, "name:");
}

export const useUserTagsStore = defineStore("userTagsStore", () => {
    const { currentUser } = storeToRefs(useUserStore());
    const { hashedUserId } = useHashedUserId(currentUser);

    const db = new UserTagStoreDatabase();
    const tags = ref<StoredTag[]>([]);
    const dbLoaded = ref(false);

    watch(
        () => hashedUserId.value,
        async (userHash) => {
            if (userHash) {
                tags.value = await db.tags.where("userHash").equals(userHash).sortBy("lastUsed");

                if (tags.value.length > maxDbEntriesPerUser) {
                    await removeOldestEntries(tags.value.length - maxDbEntriesPerUser);
                }

                dbLoaded.value = true;
            }
        },
        { immediate: true }
    );

    /** removes the x oldest tags from the database */
    async function removeOldestEntries(count: number) {
        const oldestTags = tags.value.splice(0, count);
        await db.tags.bulkDelete(oldestTags.map((o) => o.id!));
    }

    /** tags as string array */
    const userTags = computed(() => {
        return tags.value.map((o) => o.tag).reverse();
    });

    async function onNewTagSeen(tag: string) {
        await until(dbLoaded).toBe(true);

        assertDefined(hashedUserId.value);
        tag = normalizeTag(tag);

        const tagSet = new Set(userTags.value);

        if (!tagSet.has(tag)) {
            const tagObject: StoredTag = {
                tag,
                userHash: hashedUserId.value,
                lastUsed: Date.now(),
            };

            tags.value.push(tagObject);
            await db.tags.add(tagObject);
        }
    }

    async function onMultipleNewTagsSeen(newTags: string[]) {
        await until(dbLoaded).toBe(true);

        const userHash = ensureDefined(hashedUserId.value);
        const tagSet = new Set(userTags.value);

        // only the ones that really are new
        const filteredNewTags = newTags.map(normalizeTag).filter((tag) => !tagSet.has(tag));

        if (filteredNewTags.length > 0) {
            const now = Date.now();
            const newTagObjects: StoredTag[] = filteredNewTags.map((tag) => ({
                tag,
                userHash,
                lastUsed: now,
            }));

            tags.value = tags.value.concat(newTagObjects);
            await db.tags.bulkAdd(newTagObjects);
        }
    }

    async function onTagUsed(tag: string) {
        await until(dbLoaded).toBe(true);
        tag = normalizeTag(tag);

        const dbTag = await db.tags.get({ tag });

        if (dbTag) {
            await db.tags.update(dbTag, { lastUsed: Date.now() });
        } else {
            const storedTag = tags.value.find((o) => o.tag === tag);
            const id = storedTag?.id;

            if (id !== undefined) {
                await db.tags.add({ ...storedTag, lastUsed: Date.now() } as StoredTag);
            }
        }
    }

    return { userTags, onNewTagSeen, onTagUsed, onMultipleNewTagsSeen };
});

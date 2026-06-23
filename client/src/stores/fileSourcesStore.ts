import { defineStore } from "pinia";
import { ref } from "vue";

import { type BrowsableFilesSourcePlugin, fetchFileSources, type FilterFileSourcesOptions } from "@/api/remoteFiles";

export const useFileSourcesStore = defineStore("fileSourcesStore", () => {
    const cachedFileSources = ref<{
        [key: string]: BrowsableFilesSourcePlugin[] | Promise<BrowsableFilesSourcePlugin[]>;
    }>({});

    async function getFileSources(options: FilterFileSourcesOptions = {}): Promise<BrowsableFilesSourcePlugin[]> {
        const cacheKey = getCacheKey(options);
        if (cachedFileSources.value[cacheKey] === undefined) {
            cachedFileSources.value[cacheKey] = fetchFileSources(options);
        }
        if (cachedFileSources.value[cacheKey] instanceof Promise) {
            cachedFileSources.value[cacheKey] = await cachedFileSources.value[cacheKey]!;
        }
        return cachedFileSources.value[cacheKey]!;
    }

    function getCacheKey(options: FilterFileSourcesOptions) {
        return JSON.stringify(options);
    }

    return {
        getFileSources,
    };
});

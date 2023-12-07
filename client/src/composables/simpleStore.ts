import { computed, del, ref, set } from "vue";

import type { ApiResponse } from "@/api/schema";

interface FetchParams {
    id: string;
}

interface FetchFunction<T> {
    (params: FetchParams): Promise<ApiResponse<T>>;
}

interface ShouldFetch<T> {
    (item?: T): boolean;
}

export function useSimpleKeyStore<T>(fetchItem: FetchFunction<T>, shouldFetch: ShouldFetch<T> = (item) => !item) {
    const storedItems = ref<{ [key: string]: T }>({});
    const loadingItem = ref<{ [key: string]: boolean }>({});

    const getItemById = computed(() => {
        return (id: string) => {
            const item = storedItems.value[id];
            if (!loadingItem.value[id] && shouldFetch(item)) {
                fetchItemById({ id: id });
            }
            return item ?? null;
        };
    });

    const isLoadingItem = computed(() => {
        return (id: string) => {
            return loadingItem.value[id] ?? false;
        };
    });

    async function fetchItemById(params: FetchParams) {
        const itemId = params.id;
        set(loadingItem.value, itemId, true);
        try {
            const { data } = await fetchItem({ id: itemId });
            set(storedItems.value, itemId, data);
            return data;
        } finally {
            del(loadingItem.value, itemId);
        }
    }

    return {
        storedItems,
        getItemById,
        isLoadingItem,
        fetchItemById,
    };
}

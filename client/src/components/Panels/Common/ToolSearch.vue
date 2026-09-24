<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { nextTick } from "vue";
import { onMounted, onUnmounted, type PropType, watch } from "vue";

import { FAVORITES_KEYS, filterPanelByToolIds, searchTools } from "@/components/Panels/utilities";
import { type Tool, type ToolPanelItem, type ToolSection, useToolStore } from "@/stores/toolStore";
import { useUserStore } from "@/stores/userStore";
import _l from "@/utils/localization";

import DelayedInput from "@/components/Common/DelayedInput.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const MIN_QUERY_LENGTH = 3;

const props = defineProps({
    currentPanelView: {
        type: String,
        required: true,
    },
    placeholder: {
        type: String,
        default: "search tools",
    },
    query: {
        type: String,
        default: null,
    },
    queryPending: {
        type: Boolean,
        default: false,
    },
    toolsList: {
        type: Array as PropType<Tool[]>,
        required: true,
    },
    currentPanel: {
        type: Object as PropType<Record<string, ToolPanelItem>>,
        required: true,
    },
    useWorker: {
        type: Boolean,
        default: false,
    },
});

const emit = defineEmits<{
    (
        e: "onResults",
        filtered: string[] | null,
        sectioned: Record<string, Tool | ToolSection> | null,
        closestValue: string | null,
    ): void;
    (e: "onQuery", query: string): void;
}>();

const { currentFavorites } = storeToRefs(useUserStore());
const toolStore = useToolStore();
const { searchWorker } = storeToRefs(toolStore);

interface RequestPayload {
    tools: Tool[];
    query: string;
    currentPanel: Record<string, ToolPanelItem>;
}

interface SearchEventQuery {
    type: "searchTools";
    payload: RequestPayload;
}

interface SearchEventClear {
    type: "clearFilter";
}

interface SearchEventFavorite {
    type: "favoriteTools";
}

type SearchEventData = SearchEventQuery | SearchEventClear | SearchEventFavorite;

interface SearchEvent {
    data: SearchEventData;
}

interface ResponsePayloadResults {
    type: "searchToolsByKeysResult";
    payload: string[];
    query: string;
    closestTerm: string | null;
    sectioned: Record<string, Tool | ToolSection> | null;
}

interface ResponseClearFilter {
    type: "clearFilterResult";
}

interface ResponseFavoriteTools {
    type: "favoriteToolsResult";
}

interface ResponseFavoriteSearchResults {
    type: "favoriteSearchToolsResult";
    payload: string[];
    query: string;
    closestTerm: string | null;
    sectioned: Record<string, Tool | ToolSection> | null;
}

type ResponsePayloadData =
    | ResponsePayloadResults
    | ResponseClearFilter
    | ResponseFavoriteTools
    | ResponseFavoriteSearchResults;

interface ResponsePayload {
    type: "message";
    data: ResponsePayloadData;
}

function parseFavoritesQuery(query: string) {
    const trimmedQuery = query.trim();
    const favoritesToken = FAVORITES_KEYS.find((token) => trimmedQuery.toLowerCase().startsWith(token));
    if (!favoritesToken) {
        return null;
    }

    const remainder = trimmedQuery
        .slice(favoritesToken.length)
        .trim()
        .replace(/^AND\s+/i, "")
        .trim();
    return {
        isFavoritesOnly: remainder.length === 0,
        remainder,
    };
}

function handlePost(event: SearchEvent) {
    const { type } = event.data;
    if (type === "searchTools") {
        const { tools, query, currentPanel } = event.data.payload;
        const favoritesQuery = parseFavoritesQuery(query);
        if (favoritesQuery && !favoritesQuery.isFavoritesOnly) {
            const { results, resultPanel, closestTerm } = searchTools(tools, favoritesQuery.remainder, currentPanel);
            const favoriteToolIdSet = new Set(currentFavorites.value.tools);
            const favoriteResults = results.filter((toolId) => favoriteToolIdSet.has(toolId));
            const favoriteResultPanel =
                resultPanel && favoriteResults.length > 0
                    ? filterPanelByToolIds(resultPanel, new Set(favoriteResults))
                    : resultPanel;
            onMessage({
                data: {
                    type: "favoriteSearchToolsResult",
                    payload: favoriteResults,
                    sectioned: favoriteResultPanel,
                    query,
                    closestTerm,
                },
            } as unknown as MessageEvent);
            return;
        }
        const { results, resultPanel, closestTerm } = searchTools(tools, query, currentPanel);
        // send the result back to the main thread
        onMessage({
            data: {
                type: "searchToolsByKeysResult",
                payload: results.slice(),
                sectioned: resultPanel,
                query: query,
                closestTerm: closestTerm,
            },
        } as unknown as MessageEvent);
    } else if (type === "clearFilter") {
        onMessage({ data: { type: "clearFilterResult" } } as unknown as MessageEvent);
    } else if (type === "favoriteTools") {
        onMessage({ data: { type: "favoriteToolsResult" } } as unknown as MessageEvent);
    }
}

function onMessage(event: MessageEvent) {
    const type = (event as unknown as ResponsePayload).data.type;
    if (type === "searchToolsByKeysResult") {
        const data = event.data as ResponsePayloadResults;
        const { payload, sectioned, query, closestTerm } = data;
        if (query === props.query) {
            emit("onResults", payload, sectioned, closestTerm);
        }
    } else if (type === "favoriteSearchToolsResult") {
        const data = event.data as ResponseFavoriteSearchResults;
        const { payload, sectioned, query, closestTerm } = data;
        if (query === props.query) {
            emit("onResults", payload, sectioned, closestTerm);
        }
    } else if (type === "clearFilterResult") {
        emit("onResults", null, null, null);
    } else if (type === "favoriteToolsResult") {
        emit("onResults", currentFavorites.value.tools, null, null);
    }
}

onMounted(() => {
    if (props.useWorker) {
        // initialize worker
        if (!searchWorker.value) {
            searchWorker.value = new Worker(new URL("../toolSearch.worker.js", import.meta.url), { type: "module" });
        }
        searchWorker.value.onmessage = onMessage;
    }
});

onUnmounted(() => {
    // The worker is not terminated but it will not be listening to messages
    if (searchWorker.value?.onmessage) {
        searchWorker.value.onmessage = null;
    }
});

watch(
    () => currentFavorites.value.tools,
    () => {
        const favoritesQuery = parseFavoritesQuery(props.query);
        if (!favoritesQuery) {
            return;
        }
        if (favoritesQuery.isFavoritesOnly) {
            post({ type: "favoriteTools" });
        } else {
            post({
                type: "searchTools",
                payload: {
                    tools: props.toolsList,
                    query: props.query,
                    currentPanel: props.currentPanel,
                },
            });
        }
    },
);

function checkQuery(q: string) {
    emit("onQuery", q);
    if (q.trim() && q.trim().length >= MIN_QUERY_LENGTH) {
        const favoritesQuery = parseFavoritesQuery(q);
        if (favoritesQuery?.isFavoritesOnly) {
            post({ type: "favoriteTools" });
        } else {
            post({
                type: "searchTools",
                payload: {
                    tools: props.toolsList,
                    query: q,
                    currentPanel: props.currentPanel,
                },
            });
        }
    } else {
        post({ type: "clearFilter" });
    }
}

function post(message: object) {
    if (props.useWorker) {
        searchWorker.value?.postMessage(message);
    } else {
        nextTick(() => {
            handlePost({ data: message as SearchEventData });
        });
    }
}
</script>

<template>
    <div v-if="searchWorker || !props.useWorker">
        <DelayedInput
            class="mb-3"
            :value="props.query"
            :delay="200"
            :loading="queryPending"
            :placeholder="placeholder"
            @change="checkQuery" />
    </div>
    <BAlert v-else class="mb-3" variant="info" show>
        <LoadingSpan message="Loading Tool Search" />
    </BAlert>
</template>

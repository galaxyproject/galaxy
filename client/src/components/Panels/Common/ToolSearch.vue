<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { nextTick } from "vue";
import { onMounted, onUnmounted, type PropType, watch } from "vue";

import { searchToolsByKeys } from "@/components/Panels/utilities";
import { type Tool, type ToolSection, useToolStore } from "@/stores/toolStore";
import { useUserStore } from "@/stores/userStore";
import _l from "@/utils/localization";

import type { ToolSearchKeys } from "../utilities";

import DelayedInput from "@/components/Common/DelayedInput.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

// Note: These are ordered by result priority (exact matches very top; words matches very bottom)
const KEYS: ToolSearchKeys = { exact: 5, startsWith: 4, name: 3, description: 2, combined: 1, wordMatch: 0 };

const FAVORITES = ["#favs", "#favorites", "#favourites"];
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
        type: Object as PropType<Record<string, Tool | ToolSection>>,
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

interface RequestPaylod {
    tools: Tool[];
    keys: ToolSearchKeys;
    query: string;
    panelView: string;
    currentPanel: Record<string, Tool | ToolSection>;
}

interface SearchEventQuery {
    type: "searchToolsByKeys";
    payload: RequestPaylod;
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

type ResponsePayloadData = ResponsePayloadResults | ResponseClearFilter | ResponseFavoriteTools;

interface ResponsePayload {
    type: "message";
    data: ResponsePayloadData;
}

function handlePost(event: SearchEvent) {
    const { type } = event.data;
    if (type === "searchToolsByKeys") {
        const { tools, keys, query, panelView, currentPanel } = event.data.payload;
        const { results, resultPanel, closestTerm } = searchToolsByKeys(tools, keys, query, panelView, currentPanel);
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
            searchWorker.value = new Worker(new URL("components/Panels/toolSearch.worker.js", import.meta.url));
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
        if (FAVORITES.includes(props.query)) {
            post({ type: "favoriteTools" });
        }
    },
);

function checkQuery(q: string) {
    emit("onQuery", q);
    if (q.trim() && q.trim().length >= MIN_QUERY_LENGTH) {
        if (FAVORITES.includes(q)) {
            post({ type: "favoriteTools" });
        } else {
            post({
                type: "searchToolsByKeys",
                payload: {
                    tools: props.toolsList,
                    keys: KEYS,
                    query: q,
                    panelView: props.currentPanelView,
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

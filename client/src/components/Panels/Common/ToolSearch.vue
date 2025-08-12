<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { nextTick } from "vue";
import { onMounted, onUnmounted, type PropType, watch } from "vue";

import { FAVORITES_KEYS, searchTools } from "@/components/Panels/utilities";
import { type Tool, type ToolSection, useToolStore } from "@/stores/toolStore";
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

interface RequestPayload {
    tools: Tool[];
    query: string;
    currentPanel: Record<string, Tool | ToolSection>;
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

type ResponsePayloadData = ResponsePayloadResults | ResponseClearFilter | ResponseFavoriteTools;

interface ResponsePayload {
    type: "message";
    data: ResponsePayloadData;
}

function handlePost(event: SearchEvent) {
    const { type } = event.data;
    if (type === "searchTools") {
        const { tools, query, currentPanel } = event.data.payload;
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
        if (FAVORITES_KEYS.includes(props.query)) {
            post({ type: "favoriteTools" });
        }
    },
);

function checkQuery(q: string) {
    emit("onQuery", q);
    if (q.trim() && q.trim().length >= MIN_QUERY_LENGTH) {
        if (FAVORITES_KEYS.includes(q)) {
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
        <FilterMenu
            v-if="props.enableAdvanced"
            :class="!propShowAdvanced && 'mb-3'"
            name="Tools"
            :placeholder="props.placeholder"
            :debounce-delay="200"
            :filter-class="ToolFilters"
            v-model:filter-text="localFilterText"
            has-help
            :loading="props.queryPending"
            v-model:show-advanced="propShowAdvanced"
            menu-type="separate"
            @on-search="onAdvancedSearch">
            <template v-slot:menu-help-text>
                <div>
                    <p>
                        You can use this Advanced Tool Search Panel to find tools by applying search filters, with the
                        results showing up in the center panel.
                    </p>

                    <p>
                        <i>
                            (Clicking on the Section, Repo or Owner labels in the Search Results will activate the
                            according filter)
                        </i>
                    </p>

                    <p>The available tool search filters are:</p>
                    <dl>
                        <dt><code>name</code></dt>
                        <dd>The tool name (stored as tool.name + tool.description in the XML)</dd>
                        <dt><code>section</code></dt>
                        <dd>The tool section is based on the default tool panel view</dd>
                        <dt><code>ontology</code></dt>
                        <dd>
                            This is the EDAM ontology term that is associated with the tool. Example inputs:
                            <i>"topic_3174"</i> or <i>"operation_0324"</i>
                        </dd>
                        <dt><code>id</code></dt>
                        <dd>The tool id (taken from its XML)</dd>
                        <dt><code>owner</code></dt>
                        <dd>
                            For the tools that have been installed from the
                            <a href="https://toolshed.g2.bx.psu.edu/" target="_blank">ToolShed</a>
                            , this <i>owner</i> filter allows you to search for tools from a specific ToolShed
                            repository <b>owner</b>.
                        </dd>
                        <dt><code>help text</code></dt>
                        <dd>
                            This is like a keyword search: you can search for keywords that might exist in a tool's help
                            text. An example input:
                            <i>"genome, RNA, minimap"</i>
                        </dd>
                    </dl>
                </div>
            </template>
        </FilterMenu>
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

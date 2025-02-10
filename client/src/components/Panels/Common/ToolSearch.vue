<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { nextTick } from "vue";
import { computed, type ComputedRef, onMounted, onUnmounted, type PropType, watch } from "vue";
import { useRouter } from "vue-router/composables";

import { searchToolsByKeys } from "@/components/Panels/utilities";
import { type Tool, type ToolSection, useToolStore } from "@/stores/toolStore";
import { useUserStore } from "@/stores/userStore";
import Filtering, { contains, type ValidFilter } from "@/utils/filtering";
import _l from "@/utils/localization";

import { type ToolSearchKeys } from "../utilities";

import DelayedInput from "@/components/Common/DelayedInput.vue";
import FilterMenu from "@/components/Common/FilterMenu.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const router = useRouter();

// Note: These are ordered by result priority (exact matches very top; words matches very bottom)
const KEYS: ToolSearchKeys = { exact: 5, startsWith: 4, name: 3, description: 2, combined: 1, wordMatch: 0 };

const FAVORITES = ["#favs", "#favorites", "#favourites"];
const MIN_QUERY_LENGTH = 3;

const props = defineProps({
    currentPanelView: {
        type: String,
        required: true,
    },
    enableAdvanced: {
        type: Boolean,
        default: false,
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
    showAdvanced: {
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
    (e: "update:show-advanced", showAdvanced: boolean): void;
    (
        e: "onResults",
        filtered: string[] | null,
        sectioned: Record<string, Tool | ToolSection> | null,
        closestValue: string | null
    ): void;
    (e: "onQuery", query: string): void;
}>();

const localFilterText = computed({
    get: () => {
        return props.query !== null ? props.query : "";
    },
    set: (newVal: any) => {
        if (newVal.trim() || props.query.trim()) {
            checkQuery(newVal);
        }
    },
});

const propShowAdvanced = computed({
    get: () => {
        return props.showAdvanced;
    },
    set: (val: boolean) => {
        emit("update:show-advanced", val);
    },
});
const validFilters: ComputedRef<Record<string, ValidFilter<string>>> = computed(() => {
    return {
        name: { placeholder: "name", type: String, handler: contains("name"), menuItem: true },
        section: {
            placeholder: "section",
            type: String,
            handler: contains("section"),
            datalist: sectionNames,
            menuItem: true,
        },
        ontology: {
            placeholder: "EDAM ontology",
            type: String,
            handler: contains("ontology"),
            datalist: ontologyList.value,
            menuItem: true,
        },
        id: { placeholder: "id", type: String, handler: contains("id"), menuItem: true },
        owner: { placeholder: "repository owner", type: String, handler: contains("owner"), menuItem: true },
        help: { placeholder: "help text", type: String, handler: contains("help"), menuItem: true },
    };
});
const ToolFilters: ComputedRef<Filtering<string>> = computed(() => new Filtering(validFilters.value));

const { currentFavorites } = storeToRefs(useUserStore());
const toolStore = useToolStore();
const { searchWorker } = storeToRefs(toolStore);

const sectionNames = toolStore.sectionDatalist("default").map((option: { value: string; text: string }) => option.text);
const ontologyList = computed(() =>
    toolStore.sectionDatalist("ontology:edam_topics").concat(toolStore.sectionDatalist("ontology:edam_operations"))
);

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
    }
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

function onAdvancedSearch(filters: any) {
    router.push({ path: "/tools/list", query: filters });
}
</script>

<template>
    <div v-if="searchWorker || !props.userWorker">
        <FilterMenu
            v-if="props.enableAdvanced"
            :class="!propShowAdvanced && 'mb-3'"
            name="Tools"
            :placeholder="props.placeholder"
            :debounce-delay="200"
            :filter-class="ToolFilters"
            :filter-text.sync="localFilterText"
            has-help
            :loading="props.queryPending"
            :show-advanced.sync="propShowAdvanced"
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
            v-else
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

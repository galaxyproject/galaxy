<script setup lang="ts">
import { computed, type ComputedRef, onMounted, onUnmounted, type PropType, type Ref, ref } from "vue";
import { useRouter } from "vue-router/composables";

import { getGalaxyInstance } from "@/app";
import Filtering, { contains, type ValidFilter } from "@/utils/filtering";

import { flattenTools } from "../utilities.js";

import DelayedInput from "@/components/Common/DelayedInput.vue";
import FilterMenu from "@/components/Common/FilterMenu.vue";

const router = useRouter();

const KEYS = { exact: 3, name: 2, description: 1, combined: 0 };
const FAVORITES = ["#favs", "#favorites", "#favourites"];
const MIN_QUERY_LENGTH = 3;

interface Tool {
    name?: string;
}

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
    toolbox: {
        type: Array as PropType<Tool[]>,
        required: true,
    },
});

const emit = defineEmits<{
    (e: "update:show-advanced", showAdvanced: boolean): void;
    (e: "onResults", filtered: string[] | null, closestValue: string | null): void;
    (e: "onQuery", query: string): void;
}>();

const searchWorker: Ref<Worker | undefined> = ref(undefined);

const localFilterText = computed({
    get: () => {
        return props.query !== null ? props.query : "";
    },
    set: (newVal: any) => {
        checkQuery(newVal);
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
const sectionNames = computed(() => {
    return props.toolbox.map((section) =>
        section.name !== undefined && section.name !== "Uncategorized" ? section.name : ""
    );
});
const toolsList = computed(() => {
    return flattenTools(props.toolbox);
});
const validFilters: ComputedRef<Record<string, ValidFilter<string>>> = computed(() => {
    return {
        name: { placeholder: "name", type: String, handler: contains("name"), menuItem: true },
        section: {
            placeholder: props.currentPanelView === "default" ? "section" : "ontology",
            type: String,
            handler: contains("section"),
            datalist: sectionNames.value,
            menuItem: true,
        },
        id: { placeholder: "id", type: String, handler: contains("id"), menuItem: true },
        owner: { placeholder: "repository owner", type: String, handler: contains("owner"), menuItem: true },
        help: { placeholder: "help text", type: String, handler: contains("help"), menuItem: true },
    };
});
const ToolFilters: ComputedRef<Filtering<string>> = computed(() => new Filtering(validFilters.value));

onMounted(() => {
    searchWorker.value = new Worker(new URL("../toolSearch.worker.js", import.meta.url));
    const Galaxy = getGalaxyInstance();
    const favoritesResults = Galaxy?.user.getFavorites().tools;

    searchWorker.value.onmessage = ({ data }) => {
        const { type, payload, query, closestTerm } = data;
        if (type === "searchToolsByKeysResult" && query === props.query) {
            emit("onResults", payload, closestTerm);
        } else if (type === "clearFilterResult") {
            emit("onResults", null, null);
        } else if (type === "favoriteToolsResult") {
            emit("onResults", favoritesResults, null);
        }
    };
});

onUnmounted(() => {
    searchWorker.value?.terminate();
});

function checkQuery(q: string) {
    emit("onQuery", q);
    if (q && q.length >= MIN_QUERY_LENGTH) {
        if (FAVORITES.includes(q)) {
            post({ type: "favoriteTools" });
        } else {
            post({
                type: "searchToolsByKeys",
                payload: {
                    tools: toolsList.value,
                    keys: KEYS,
                    query: q,
                },
            });
        }
    } else {
        post({ type: "clearFilter" });
    }
}

function post(message: object) {
    searchWorker.value?.postMessage(message);
}

function onAdvancedSearch(filters: any, filterText?: string) {
    router.push({ path: "/tools/list", query: filters });
}
</script>

<template>
    <div>
        <FilterMenu
            v-if="props.enableAdvanced"
            :class="!propShowAdvanced && 'mb-3'"
            name="Tool Search"
            :placeholder="props.placeholder"
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
                        <dd>
                            The tool section is based on the current view you have selected for the panel. <br />
                            When this field is active, you will be able to see a datalist showing the available sections
                            you can filter from. <br />
                            By default, Galaxy tool panel sections are filterable if you are currently on the
                            <i>Full Tool Panel</i> view, and it will show EDAM ontologies or EDAM topics if you have
                            either of those options selected. <br />
                            Change panel views by clicking on the
                            <icon icon="caret-down" />
                            icon at the top right of the tool panel.
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
            :query="props.query"
            :delay="100"
            :loading="queryPending"
            :placeholder="placeholder"
            @change="checkQuery" />
    </div>
</template>

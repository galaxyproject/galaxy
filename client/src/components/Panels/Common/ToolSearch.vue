<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted, type PropType, type Ref } from "vue";
import { flattenTools } from "../utilities.js";
import DelayedInput from "@/components/Common/DelayedInput.vue";
import _l from "@/utils/localization";
import { useRouter } from "vue-router/composables";
import { getGalaxyInstance } from "@/app";

const router = useRouter();

const KEYS = { exact: 3, name: 2, description: 1, combined: 0 };
const FAVORITES = ["#favs", "#favorites", "#favourites"];
const MIN_QUERY_LENGTH = 3;

interface Tool {
    name?: string;
}
interface FilterSettings {
    [key: string]: any;
    name?: string;
    section?: string;
    id?: string;
    help?: string;
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

const filterSettings: Ref<FilterSettings> = ref({});
const showHelp: Ref<boolean> = ref(false);
const searchWorker: Ref<Worker | undefined> = ref(undefined);

const sectionNames = computed(() => {
    return props.toolbox.map((section) =>
        section.name !== undefined && section.name !== "Uncategorized" ? section.name : ""
    );
});
const sectionLabel = computed(() => {
    return props.currentPanelView === "default" ? "section" : "ontology";
});
const toolsList = computed(() => {
    return flattenTools(props.toolbox);
});

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
    filterSettings.value["name"] = q;
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

function onSearch() {
    for (const [filter, value] of Object.entries(filterSettings.value)) {
        if (!value) {
            delete filterSettings.value[filter];
        }
    }
    router.push({ path: "/tools/list", query: filterSettings.value });
}

function onToggle(toggleAdvanced: boolean) {
    emit("update:show-advanced", toggleAdvanced);
}
</script>

<template>
    <div>
        <small v-if="showAdvanced">Filter by name:</small>
        <DelayedInput
            :class="!showAdvanced && 'mb-3'"
            :query="query"
            :delay="100"
            :loading="queryPending"
            :show-advanced="showAdvanced"
            :enable-advanced="enableAdvanced"
            :placeholder="showAdvanced ? 'any name' : placeholder"
            @change="checkQuery"
            @onToggle="onToggle" />
        <div
            v-if="showAdvanced"
            description="advanced tool filters"
            @keyup.enter="onSearch"
            @keyup.esc="onToggle(false)">
            <small class="mt-1">Filter by {{ sectionLabel }}:</small>
            <b-form-input
                v-model="filterSettings['section']"
                autocomplete="off"
                size="sm"
                :placeholder="`any ${sectionLabel}`"
                list="sectionSelect" />
            <b-form-datalist id="sectionSelect" :options="sectionNames"></b-form-datalist>
            <small class="mt-1">Filter by id:</small>
            <b-form-input v-model="filterSettings['id']" size="sm" placeholder="any id" />
            <small class="mt-1">Filter by repository owner:</small>
            <b-form-input v-model="filterSettings['owner']" size="sm" placeholder="any owner" />
            <small class="mt-1">Filter by help text:</small>
            <b-form-input v-model="filterSettings['help']" size="sm" placeholder="any help text" />
            <div class="mt-3">
                <b-button class="mr-1 filter-search-btn" size="sm" variant="primary" @click="onSearch">
                    <icon icon="search" />
                    <span>{{ _l("Search") }}</span>
                </b-button>
                <b-button size="sm" @click="onToggle(false)">
                    <icon icon="redo" />
                    <span>{{ _l("Cancel") }}</span>
                </b-button>
                <b-button title="Search Help" size="sm" @click="showHelp = true">
                    <icon icon="question" />
                </b-button>
                <b-modal v-model="showHelp" title="Tool Advanced Search Help" ok-only>
                    <div>
                        <p>
                            You can use this Advanced Tool Search Panel to find tools by applying search filters, with
                            the results showing up in the center panel.
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
                                When this field is active, you will be able to see a datalist showing the available
                                sections you can filter from. <br />
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
                                This is like a keyword search: you can search for keywords that might exist in a tool's
                                help text. An example input:
                                <i>"genome, RNA, minimap"</i>
                            </dd>
                        </dl>
                    </div>
                </b-modal>
            </div>
        </div>
    </div>
</template>

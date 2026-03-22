<script setup lang="ts">
import { faBars, faGripVertical, faSitemap, faStar } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { storeToRefs } from "pinia";
import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router/composables";

import { type FilterSettings, type Tool, useToolStore } from "@/stores/toolStore";
import { type ListViewMode, useUserStore } from "@/stores/userStore";
import Filtering, { contains, type ValidFilter } from "@/utils/filtering";

import { buildToolTagClause, createWhooshQuery, FAVORITES_KEYS } from "../Panels/utilities";

import GButton from "../BaseComponents/GButton.vue";
import GButtonGroup from "../BaseComponents/GButtonGroup.vue";
import FilterMenu from "../Common/FilterMenu.vue";
import Heading from "../Common/Heading.vue";
import ToolsListSectionFilters from "./ToolsListSectionFilters.vue";
import ToolsListTable from "./ToolsListTable.vue";

interface Props {
    name?: string;
    ontology?: string;
    id?: string;
    owner?: string;
    help?: string;
    tag?: string | string[];
    search?: string;
}

const props = withDefaults(defineProps<Props>(), {
    name: "",
    ontology: "",
    id: "",
    owner: "",
    help: "",
    search: "",
});

const router = useRouter();

const userStore = useUserStore();
const { isAnonymous, currentListViewPreferences } = storeToRefs(userStore);

const currentListViewMode = computed(() => currentListViewPreferences.value["tools"] || "list");

const toolStore = useToolStore();
const { loading } = storeToRefs(toolStore);

// Filtering Classes and Definitions
const ontologyList = computed(() =>
    toolStore.sectionDatalist("ontology:edam_topics").concat(toolStore.sectionDatalist("ontology:edam_operations")),
);
const tagAutocompleteValues = computed(() =>
    [...new Set(Object.values(toolStore.toolsById).flatMap((tool) => tool.tool_tags || []))].sort((left, right) =>
        left.localeCompare(right),
    ),
);

function normalizeToolTagValue(tag: string | string[]) {
    return String(tag)
        .trim()
        .replace(/^"(.*)"$/, "$1")
        .replace(/^'(.*)'$/, "$1");
}

function quoteToolTagValue(tag: string | string[]): string | string[] {
    const normalizedValue = normalizeToolTagValue(tag);
    return /\s/.test(normalizedValue) ? `"${normalizedValue.replace(/"/g, '\\"')}"` : normalizedValue;
}

function normalizeInlineFilterValue(value: string) {
    const normalized = value.trim().replace(/^"(.*)"$/, "$1").replace(/^'(.*)'$/, "$1");
    return /[\s,]/.test(normalized) ? `"${normalized.replace(/"/g, '\\"')}"` : normalized;
}

function buildInlineWhooshClause(key: string, value: string) {
    const normalizedValue = normalizeInlineFilterValue(value);

    if (key === "tag") {
        return buildToolTagClause(value);
    }
    if (key === "ontology") {
        if (value.includes("operation")) {
            return `edam_operations:(${normalizedValue})`;
        }
        if (value.includes("topic")) {
            return `edam_topics:(${normalizedValue})`;
        }
    }
    if (key === "id") {
        return `id_exact:(${normalizedValue})`;
    }
    if (key === "name") {
        return `(name:(${normalizedValue}) name_exact:(${normalizedValue}) description:(${normalizedValue}))`;
    }

    return `${key}:(${normalizedValue})`;
}

type InlineFilterClause = {
    key: string;
    value: string;
};

function parseInlineFilterClauses(searchText: string) {
    const clauses: InlineFilterClause[] = [];
    const filterClause = /(^|\s)((tag|ontology|id|owner|help|name):(?:"([^"]*)"|'([^']*)'|([^\s"']+)))/g;
    let consumedText = "";
    let cursor = 0;
    let match;

    while ((match = filterClause.exec(searchText)) !== null) {
        const [fullMatch, leadingWhitespace = "", , key = "", quotedDouble, quotedSingle, unquotedValue] = match;
        const clauseStart = match.index + leadingWhitespace.length;
        const clauseLength = fullMatch.length - leadingWhitespace.length;
        const value = quotedDouble ?? quotedSingle ?? unquotedValue;

        if (value) {
            clauses.push({ key, value });
        }

        consumedText += searchText.slice(cursor, clauseStart);
        consumedText += " ".repeat(clauseLength);
        cursor = clauseStart + clauseLength;
    }

    if (clauses.length === 0) {
        return null;
    }

    consumedText += searchText.slice(cursor);
    const remainder = consumedText.replace(/\s+/g, " ").trim();

    return {
        remainder,
        clauses,
    };
}

function hasExplicitBooleanQuery(searchText: string) {
    return /\b(?:AND|OR|NOT)\b/.test(searchText);
}

function translateInlineStructuredSearch(searchText: string) {
    return searchText.replace(
        /(^|\s)((tag|ontology|id|owner|help|name):(?:"([^"]*)"|'([^']*)'|([^\s"']+)))/g,
        (_fullMatch, leadingWhitespace = "", _clause, key = "", quotedDouble, quotedSingle, unquotedValue) => {
            const value = quotedDouble ?? quotedSingle ?? unquotedValue;
            return `${leadingWhitespace}${buildInlineWhooshClause(key, value)}`;
        },
    );
}

function buildMixedStructuredWhooshQuery(searchText: string) {
    const parsed = parseInlineFilterClauses(searchText);
    if (!parsed || !parsed.remainder) {
        return null;
    }

    const translatedClauses = parsed.clauses.map(({ key, value }) => buildInlineWhooshClause(key, value));
    const filtersClause = translatedClauses.length > 1 ? `(${translatedClauses.join(" AND ")})` : translatedClauses[0];
    return `(${parsed.remainder}) AND (${filtersClause})`;
}

const validFilters = computed<Record<string, ValidFilter<string | string[]>>>(() => {
    return {
        name: { placeholder: "name", type: String, handler: contains("name"), menuItem: true },
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
        tag: {
            placeholder: "tag",
            type: "MultiTags",
            handler: contains("tag", undefined, quoteToolTagValue),
            menuItem: false,
        },
    };
});
// TODO: We need to use double quotes as opposed to the default single quotes in the Filtering class
// (will need to implement this in the Filtering class). We need this because the whoosh query
// requires double quotes for phrases.
// See: https://whoosh.readthedocs.io/en/latest/querylang.html#query
// For now, I've changed the `quoteStrings` param to `false` to avoid issues with the quotes, and added
// a "hint" to the `FilterMenu` help text.
const ToolFilters = computed<Filtering<string | string[]>>(
    () => new Filtering(validFilters.value, undefined, false, false),
);

function normalizePropsToFilterSettings(routeProps: Props): FilterSettings {
    const filters: FilterSettings = {};
    const stringFilters: Array<keyof Pick<Props, "name" | "ontology" | "id" | "owner" | "help">> = [
        "name",
        "ontology",
        "id",
        "owner",
        "help",
    ];

    for (const key of stringFilters) {
        const value = routeProps[key];
        if (value) {
            filters[key] = value;
        }
    }

    const tags = Array.isArray(routeProps.tag) ? routeProps.tag.filter(Boolean) : routeProps.tag ? [routeProps.tag] : [];
    if (tags.length > 0) {
        filters.tag = tags;
    }

    return filters;
}

function normalizeFilterSettings(settings: FilterSettings): FilterSettings {
    const normalized: FilterSettings = { ...settings };

    if (Array.isArray(normalized.tag)) {
        const tags = normalized.tag.filter(Boolean).map(normalizeToolTagValue);
        if (tags.length > 0) {
            normalized.tag = tags;
        } else {
            delete normalized.tag;
        }
    } else {
        delete normalized.tag;
    }

    return normalized;
}

/** The filters derived from the `filterText` via the `Filtering` class. */
const filterSettings = computed<FilterSettings>(() =>
    normalizeFilterSettings(Object.fromEntries(ToolFilters.value.getFiltersForText(filterText.value)) as FilterSettings),
);

// `FilterMenu` Component Props
const showAdvanced = ref(false);
const initialFilters = normalizePropsToFilterSettings(props);
const filterText = ref(
    ToolFilters.value.applyFiltersToText(initialFilters as Record<string, string | string[]>, "") || props.search,
);
const toolFilterMenu = ref<InstanceType<typeof FilterMenu> | null>(null);
const initialFocusDone = ref(false);

// Focus the input element, so that it is ready for user input (user can continue typing as results are filtered)
watch(
    () => toolFilterMenu.value,
    (newVal) => {
        if (newVal && !initialFocusDone.value) {
            newVal.$el?.querySelector("input")?.focus();
            initialFocusDone.value = true;
        }
    },
    { immediate: true },
);

const showFavorites = computed(() => FAVORITES_KEYS.includes(filterText.value.trim()));
const favoritesButtonTitle = computed(() => (showFavorites.value ? "Hide favorite tools" : "Show favorite tools"));
const translatedBooleanWhooshQuery = computed(() =>
    hasExplicitBooleanQuery(filterText.value) ? translateInlineStructuredSearch(filterText.value.trim()) : null,
);
const mixedStructuredWhooshQuery = computed(() =>
    translatedBooleanWhooshQuery.value ? null : buildMixedStructuredWhooshQuery(filterText.value.trim()),
);
const structuredFilterText = computed(() =>
    Object.keys(filterSettings.value).length
        ? ToolFilters.value.applyFiltersToText(filterSettings.value as Record<string, string | string[]>, "").trim()
        : "",
);
const shouldPreserveRawSearchText = computed(
    () =>
        (translatedBooleanWhooshQuery.value || mixedStructuredWhooshQuery.value) &&
        structuredFilterText.value !== filterText.value.trim(),
);

/** The backend whoosh query based on the current filters (if they can be derived from the text;
 * otherwise the raw search text itself). */
const whooshQuery = computed(() =>
    translatedBooleanWhooshQuery.value ||
    mixedStructuredWhooshQuery.value ||
    (Object.keys(filterSettings.value).length ? createWhooshQuery(filterSettings.value) : filterText.value.trim()),
);

/** The tools loaded from the store based on the `whooshQuery`. */
const itemsLoaded = computed<Tool[]>(() => Object.values(toolStore.getToolsById(whooshQuery.value)));

/** There is currently an active `owner:` filter */
const hasOwnerFilter = computed(() => {
    const ownerFilter = ToolFilters.value.getFilterValue(filterText.value, "owner");
    return typeof ownerFilter === "string" && Boolean(ownerFilter.replace(/^"(.*)"$/, "$1"));
});

// As soon as we have filters creating the whoosh query, or a raw search text, push search to router
watch(
    () => whooshQuery.value,
    async (newQuery) => {
        const routerParams: { path: string; query?: Record<string, string | string[]> } = { path: "/tools/list" };
        if (shouldPreserveRawSearchText.value) {
            routerParams.query = { search: filterText.value.trim() };
        } else if (Object.keys(filterSettings.value).length) {
            routerParams.query = Object.fromEntries(
                Object.entries(filterSettings.value).filter(([, value]) => value !== undefined),
            ) as Record<string, string | string[]>;
        } else if (newQuery) {
            routerParams.query = { search: filterText.value.trim() };
        }
        router.push(routerParams);
        await searchTools(newQuery);
    },
);

// The component mounts with the whooshQuery already generated; perform fetch!
searchTools(whooshQuery.value);
async function searchTools(query: string) {
    await toolStore.fetchTools(query, { includeToolTags: true });
}

function applyFilter(filter: string, value: string | string[]) {
    filterText.value = ToolFilters.value.setFilterValue(filterText.value, filter, value);
}

function onToggleView(newView: ListViewMode) {
    userStore.setListViewPreference("tools", newView);
}
</script>

<template>
    <section class="tools-list">
        <div class="mb-2">
            <div class="d-flex align-items-center justify-content-between flex-gapx-1">
                <Heading h1 separator inline size="lg" class="flex-grow-1 m-0">
                    <span v-localize>Discover Tools in this Galaxy</span>
                </Heading>

                <GButton
                    size="small"
                    outline
                    tooltip
                    tooltip-placement="bottom"
                    :disabled="loading"
                    color="blue"
                    title="Discover Tool EDAM Ontologies"
                    to="/tools/list/ontologies">
                    <FontAwesomeIcon :icon="faSitemap" />
                    Ontologies
                </GButton>
            </div>

            <div class="d-flex flex-nowrap align-items-center flex-gapx-1 py-2">
                <FilterMenu
                    ref="toolFilterMenu"
                    class="w-100"
                    name="Tools"
                    placeholder="search tools"
                    :debounce-delay="400"
                    :filter-text.sync="filterText"
                    :filter-class="ToolFilters"
                    :autocomplete-values="tagAutocompleteValues"
                    autocomplete-prefix="tag:"
                    has-help
                    :loading="loading"
                    :show-advanced.sync="showAdvanced">
                    <template v-slot:menu-help-text>
                        <div>
                            <p>
                                You can use this Advanced Tool Search Panel to find tools by applying search filters,
                                with the results showing up in the center panel.
                            </p>

                            <div>
                                Hints:
                                <ul>
                                    <li>
                                        <i>
                                            Clicking on the Ontology, Owner, or Tag labels in the search results will
                                            activate the matching filter.
                                        </i>
                                    </li>
                                    <li>
                                        <i>
                                            To find exact matches, you need to use double quotes (e.g.:
                                            <code>"Get Data"</code>) around the search term.
                                        </i>
                                    </li>
                                    <li>
                                        <i>
                                            You can write explicit boolean tag expressions directly in the search bar,
                                            for example <code>tag:collection_ops OR tag:data_cleanup</code>. Typing
                                            <code>tag:</code> will also suggest known curated tags.
                                        </i>
                                    </li>
                                </ul>
                            </div>

                            <p>The available tool search filters are:</p>
                            <dl>
                                <dt><code>name</code></dt>
                                <dd>The tool name (stored as tool.name + tool.description in the XML)</dd>
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
                                <dt><code>tag</code></dt>
                                <dd>
                                    A curated tool tag. Type it directly in the search bar, for example
                                    <code>tag:foo</code>, or use boolean expressions such as
                                    <code>tag:foo OR tag:bar</code>. Multi-word tags should be quoted, for example
                                    <code>tag:"data cleanup"</code>.
                                </dd>
                                <dt><code>help text</code></dt>
                                <dd>
                                    This is like a keyword search: you can search for keywords that might exist in a
                                    tool's help text. An example input:
                                    <i>"genome, RNA, minimap"</i>
                                </dd>
                            </dl>
                            <p>Examples:</p>
                            <ul>
                                <li>
                                    Match tools tagged with either collection work or cleanup:
                                    <code>tag:collection_ops OR tag:data_cleanup</code>
                                </li>
                                <li>
                                    Match a multi-word tag exactly:
                                    <code>tag:"data cleanup"</code>
                                </li>
                            </ul>
                        </div>
                    </template>
                </FilterMenu>

                <GButton
                    v-if="!showAdvanced && !isAnonymous"
                    id="show-favorites"
                    class="text-nowrap"
                    tooltip
                    :title="favoritesButtonTitle"
                    :pressed="showFavorites"
                    outline
                    color="blue"
                    @click="filterText = showFavorites ? '' : '#favorites'">
                    <FontAwesomeIcon :icon="faStar" fixed-width />
                    Favorites
                </GButton>
            </div>

            <ToolsListSectionFilters
                :filter-class="ToolFilters"
                :filter-text="filterText"
                :disabled="loading"
                @apply-filter="applyFilter">
                <template v-slot:list-view-controls>
                    <!-- TODO: This div here and in ListHeader.vue needs to be a reusable component -->
                    <div class="d-flex flex-gapx-1 align-items-center">
                        Display:
                        <GButtonGroup>
                            <GButton
                                id="view-grid"
                                tooltip
                                title="Grid view"
                                size="small"
                                :pressed="currentListViewMode === 'grid'"
                                outline
                                color="blue"
                                @click="onToggleView('grid')">
                                <FontAwesomeIcon :icon="faGripVertical" />
                            </GButton>

                            <GButton
                                id="view-list"
                                tooltip
                                title="List view"
                                size="small"
                                :pressed="currentListViewMode === 'list'"
                                outline
                                color="blue"
                                @click="onToggleView('list')">
                                <FontAwesomeIcon :icon="faBars" />
                            </GButton>
                        </GButtonGroup>
                    </div>
                </template>
            </ToolsListSectionFilters>
        </div>

        <div class="tools-list-body">
            <ToolsListTable
                :tools="itemsLoaded"
                :loading="loading"
                :has-owner-filter="hasOwnerFilter"
                :grid-view="currentListViewMode === 'grid'"
                @apply-filter="applyFilter" />
        </div>
    </section>
</template>

<style lang="scss" scoped>
.tools-list {
    display: flex;
    flex-flow: column;

    .tools-list-body {
        display: flex;
        flex-direction: column;
        overflow-y: auto;
    }
}
</style>

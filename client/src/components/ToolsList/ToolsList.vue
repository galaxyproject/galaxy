<script setup lang="ts">
import { faStar } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BDropdown, BDropdownItem } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref, watch } from "vue";

import { type FilterSettings, type Tool, type ToolSection, useToolStore } from "@/stores/toolStore";
import Filtering, { contains, type ValidFilter } from "@/utils/filtering";

import { createSortedResultObject, createWhooshQuery, FAVORITES_KEYS, isToolSection } from "../Panels/utilities";

import GButton from "../BaseComponents/GButton.vue";
import GLink from "../BaseComponents/GLink.vue";
import FilterMenu from "../Common/FilterMenu.vue";
import GCard from "../Common/GCard.vue";
import Heading from "../Common/Heading.vue";
import ToolsListTable from "./ToolsListTable.vue";

interface Props {
    name?: string;
    section?: string;
    ontology?: string;
    id?: string;
    owner?: string;
    help?: string;
}

const props = withDefaults(defineProps<Props>(), {
    name: "",
    section: "",
    ontology: "",
    id: "",
    owner: "",
    help: "",
});

const toolStore = useToolStore();
const { currentToolSections, currentPanelView, loading } = storeToRefs(toolStore);

// Filtering Classes and Definitions
const sectionNames = toolStore.sectionDatalist("default").map((option: { value: string; text: string }) => option.text);
const ontologyList = computed(() =>
    toolStore.sectionDatalist("ontology:edam_topics").concat(toolStore.sectionDatalist("ontology:edam_operations")),
);
const validFilters = computed<Record<string, ValidFilter<string>>>(() => {
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
// TODO: We need to use double quotes as opposed to the default single quotes in the Filtering class
// (will need to implement this in the Filtering class). We need this because the whoosh query
// requires double quotes for phrases.
// See: https://whoosh.readthedocs.io/en/latest/querylang.html#query
// For now, I've changed the `quoteStrings` param to `false` to avoid issues with the quotes, and added
// a "hint" to the `FilterMenu` help text.
const ToolFilters = computed<Filtering<string>>(() => new Filtering(validFilters.value, undefined, false, false));

/** The filters derived from the `filterText` via the `Filtering` class. */
const filterSettings = computed<FilterSettings>(() =>
    Object.fromEntries(ToolFilters.value.getFiltersForText(filterText.value)),
);

// `FilterMenu` Component Props
const showAdvanced = ref(false);
const filterText = ref(ToolFilters.value.applyFiltersToText(props, ""));

const showFavorites = computed(() => FAVORITES_KEYS.includes(filterText.value.trim()));
const favoritesButtonTitle = computed(() => (showFavorites.value ? "Hide favorite tools" : "Show favorite tools"));

/** The backend whoosh query based on the current filters (if they can be derived from the text;
 * otherwise the raw search text itself). */
const whooshQuery = computed(() =>
    Object.keys(filterSettings.value).length ? createWhooshQuery(filterSettings.value) : filterText.value.trim(),
);

/** The tools loaded from the store based on the `whooshQuery`. */
const itemsLoaded = computed<Tool[]>(() => Object.values(toolStore.getToolsById(whooshQuery.value)));

/** A section view of all tools loaded from the store. */
const allSectionsLoaded = computed<Record<string, ToolSection>>(() => {
    const matchedTools: { id: string; order: number }[] = Object.keys(toolStore.getToolsById()).map((id) => ({
        id: id,
        order: 6,
    }));
    const { resultPanel } = createSortedResultObject(matchedTools, currentToolSections.value);

    return Object.fromEntries(
        Object.entries(resultPanel).filter(([_, section]) => isToolSection(section) && section.name !== "Uncategorized")
    ) as Record<string, ToolSection>;

    // TODO: If we want sections loaded for the given query, we can add the whooshQuery param to `getToolsById`.
});

const selectedSection = computed<ToolSection | null>(() => {
    const sectionName = ToolFilters.value.getFilterValue(filterText.value, "section");
    const sectionWithMatchingName = Object.values(currentToolSections.value).find(
        (section: Tool | ToolSection) => section.name === sectionName
    );
    if (sectionWithMatchingName && isToolSection(sectionWithMatchingName)) {
        return sectionWithMatchingName;
    } else {
        const ontologyId = ToolFilters.value.getFilterValue(filterText.value, "ontology");
        const foundOntology = Object.values(currentToolSections.value).find(
            (section: Tool | ToolSection) => section.id === ontologyId
        );
        if (foundOntology && isToolSection(foundOntology)) {
            return foundOntology;
        }
    }
    return null;
});

const selectedSectionBadges = computed(() => {
    if (selectedSection.value?.id === ToolFilters.value.getFilterValue(filterText.value, "ontology")) {
        return [
            {
                id: "ontology-id",
                label: selectedSection.value!.id,
                title: "The EDAM id for this ontology",
                class: "ontology-badge",
                visible: true,
            },
        ];
    }
    return [];
});

watch(
    () => whooshQuery.value,
    async (newQuery) => {
        await toolStore.fetchTools(newQuery);
    },
    { deep: true, immediate: true },
);

// Change filter text on panel view change (because this also changes what is in the section selector)
watch(
    () => currentPanelView.value,
    () => {
        filterText.value = "";
    }
);

function applyFilter(filter: string, value: string) {
    filterText.value = ToolFilters.value.setFilterValue(filterText.value, filter, value);
}

function searchForSection(section: ToolSection) {
    if (["ontology:edam_operations", "ontology:edam_topics"].includes(currentPanelView.value)) {
        const foundOntology = ontologyList.value.find((ontology) => ontology.value === section.id);
        if (foundOntology?.text) {
            applyFilter("ontology", foundOntology.value);
        }
    } else {
        applyFilter("section", section.name);
    }
}
</script>

<template>
    <section class="tools-list">
        <div class="mb-2">
            <div class="d-flex align-items-center justify-content-between">
                <Heading h1 separator inline size="lg" class="flex-grow-1 m-0">
                    <span v-localize>Discover Tools in this Galaxy</span>
                </Heading>
            </div>

            <div class="d-flex flex-nowrap align-items-center flex-gapx-1 py-2">
                <FilterMenu
                    class="w-100"
                    name="Tools"
                    placeholder="search tools"
                    :debounce-delay="200"
                    :filter-text.sync="filterText"
                    :filter-class="ToolFilters"
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
                                            Clicking on the Section, Repo or Owner labels in the Search Results will
                                            activate the according filter.
                                        </i>
                                    </li>
                                    <li>
                                        <i>
                                            To find exact matches, you need to use double quotes (e.g.:
                                            <code>"Get Data"</code>) around the search term.
                                        </i>
                                    </li>
                                </ul>
                            </div>

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
                                    This is like a keyword search: you can search for keywords that might exist in a
                                    tool's help text. An example input:
                                    <i>"genome, RNA, minimap"</i>
                                </dd>
                            </dl>
                        </div>
                    </template>
                </FilterMenu>

                <GButton
                    v-if="!showAdvanced"
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

            <BDropdown
                block
                :disabled="loading"
                variant="link"
                class="tool-section-dropdown"
                toggle-class="text-decoration-none"
                role="menu"
                aria-label="Select a tool section to filter by"
                size="sm">
                <template v-slot:button-content>
                    <span class="sr-only">Select a tool section to filter by</span>
                    <span v-if="selectedSection">
                        {{ selectedSection.name }}
                    </span>
                    <i v-else> Select a section to filter by </i>
                </template>

                <BDropdownItem
                    v-for="sec in allSectionsLoaded"
                    :key="sec.id"
                    class="ml-1"
                    :title="sec.description"
                    :active="selectedSection?.id === sec.id"
                    @click="searchForSection(sec)">
                    <span v-localize>{{ sec.name }}</span>
                </BDropdownItem>
            </BDropdown>

            <GCard
                v-if="selectedSection?.description"
                current
                :badges="selectedSectionBadges"
                :description="selectedSection.description"
                full-description
                :title="selectedSection.name">
                <template v-slot:update-time>
                    <i v-if="selectedSection.tools">
                        {{ Math.max(selectedSection.tools.length, itemsLoaded.length) }} tools in this section

                        <!-- TODO: There can be a mismatch here, maybe try to fix. -->
                    </i>
                </template>
                <template v-slot:secondary-actions>
                    <div v-if="selectedSection.links && Object.keys(selectedSection.links).length > 0">
                        <GLink
                            v-for="(link, key) in selectedSection.links"
                            :key="key"
                            :href="link"
                            :title="link"
                            target="_blank"
                            rel="noopener noreferrer">
                            {{ key }}
                        </GLink>
                    </div>
                </template>
            </GCard>
        </div>

        <div class="tools-list-body">
            <ToolsListTable :tools="itemsLoaded" :loading="loading" @apply-filter="applyFilter" />
        </div>
    </section>
</template>

<style lang="scss" scoped>
@import "theme/blue.scss";

.tools-list {
    display: flex;
    flex-flow: column;

    .tool-section-dropdown {
        :deep(.dropdown-menu) {
            overflow: auto;
            max-height: 50vh;
            min-width: 100%;
        }
    }

    :deep(.ontology-badge) {
        background-color: scale-color($brand-toggle, $lightness: +75%);
        border-color: scale-color($brand-toggle, $lightness: +55%);
    }

    .tools-list-body {
        display: flex;
        flex-direction: column;
        overflow-y: auto;
    }
}
</style>

<script setup lang="ts">
import { faLayerGroup, faSitemap, faTimes, type IconDefinition } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BDropdown, BDropdownDivider, BDropdownGroup, BDropdownItem, BDropdownText, BFormInput } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref, watch } from "vue";

import { type ToolSection, useToolStore } from "@/stores/toolStore";
import type Filtering from "@/utils/filtering";

import { types_to_icons } from "../Panels/utilities";

import GButton from "../BaseComponents/GButton.vue";
import ToolOntologyCard from "./ToolOntologyCard.vue";

const props = defineProps<{
    /** The `Filtering` class (ToolFilters). */
    filterClass: Filtering<string>;
    /** The current filter text. */
    filterText: string;
    /** Whether the dropdowns should be disabled. */
    disabled?: boolean;
}>();

const emit = defineEmits<{
    (e: "apply-filter", filter: string, value: string): void;
}>();

const toolStore = useToolStore();
const { defaultPanelView, panels, panelSections } = storeToRefs(toolStore);

const defaultToolSectionsFilter = ref("");
const defaultToolSections = computed(() =>
    searchWithinSections(panelSections.value(defaultPanelView.value), defaultToolSectionsFilter.value),
);

const ontologiesFilter = ref("");
const edamOperations = computed(() =>
    searchWithinSections(panelSections.value("ontology:edam_operations"), ontologiesFilter.value),
);
const edamTopics = computed(() =>
    searchWithinSections(panelSections.value("ontology:edam_topics"), ontologiesFilter.value),
);

const selectedSection = computed<ToolSection | null>(() => {
    const sectionName = props.filterClass.getFilterValue(props.filterText, "section")?.replace(/^"(.*)"$/, "$1");
    return (
        Object.values(defaultToolSections.value).find((section: ToolSection) => section.name === sectionName) || null
    );
});

const selectedOntology = computed<ToolSection | null>(() => {
    const ontologyId = props.filterClass.getFilterValue(props.filterText, "ontology")?.replace(/^"(.*)"$/, "$1");
    return (
        Object.values(edamOperations.value).find((section: ToolSection) => section.id === ontologyId) ||
        Object.values(edamTopics.value).find((section: ToolSection) => section.id === ontologyId) ||
        null
    );
});

watch(
    () => defaultPanelView.value,
    (newVal) => {
        if (newVal) {
            ensureSectionsAndOntologiesLoaded();
        }
    },
    { immediate: true },
);

/** Ensures `toolStore.toolSections` contains the necessary sections to generate section dropdown filters for.
 *
 * _Note that the `toolStore` itself ensures a panel isn't loaded if it's already present in the state._
 */
async function ensureSectionsAndOntologiesLoaded() {
    await toolStore.fetchToolSections(defaultPanelView.value);

    await toolStore.fetchToolSections("ontology:edam_operations");
    await toolStore.fetchToolSections("ontology:edam_topics");
}

function getPanelIcon(panelView: string): IconDefinition | null {
    const viewType = panels.value[panelView]?.view_type;
    return viewType ? types_to_icons[viewType] : null;
}

function applyQuotedFilter(filter: string, value: string) {
    emit("apply-filter", filter, `"${value}"`);
}

function searchWithinSections(sections: ToolSection[], query: string) {
    if (query) {
        const filterLower = query.toLowerCase();
        return sections.filter((section) => section.name?.toLowerCase().includes(filterLower));
    }
    return sections;
}
</script>

<template>
    <div class="d-flex flex-column flex-gapy-1">
        <div class="d-flex justify-content-between align-items-center">
            <div class="d-flex flex-gapx-1">
                <BDropdown
                    block
                    :disabled="props.disabled"
                    variant="link"
                    class="tool-section-dropdown"
                    toggle-class="text-decoration-none"
                    role="menu"
                    aria-label="Select a tool section to filter by"
                    size="sm">
                    <template v-slot:button-content>
                        <span class="sr-only">Select a tool section to filter by</span>
                        <FontAwesomeIcon :icon="faLayerGroup" />
                        <span v-if="selectedSection">
                            {{ selectedSection.name }}
                        </span>
                        <i v-else> Select a section to filter by </i>
                    </template>

                    <BDropdownGroup
                        id="searchable-sections"
                        class="sections-select-list"
                        header-classes="search-header">
                        <template v-slot:header>
                            <BDropdownText>
                                <BFormInput
                                    v-model="defaultToolSectionsFilter"
                                    type="text"
                                    placeholder="Filter sections..." />
                            </BDropdownText>
                        </template>

                        <BDropdownItem
                            v-for="sec in defaultToolSections"
                            :key="sec.id"
                            :title="sec.description"
                            :active="selectedSection?.id === sec.id"
                            @click="applyQuotedFilter('section', sec.name)">
                            <span v-localize>{{ sec.name }}</span>
                        </BDropdownItem>
                    </BDropdownGroup>
                </BDropdown>

                <GButton
                    v-if="selectedSection"
                    title="Remove section filter"
                    icon-only
                    inline
                    transparent
                    tooltip
                    @click="applyQuotedFilter('section', selectedSection.name)">
                    <FontAwesomeIcon :icon="faTimes" />
                </GButton>

                <BDropdown
                    block
                    :disabled="props.disabled"
                    variant="link"
                    class="tool-section-dropdown"
                    toggle-class="text-decoration-none"
                    role="menu"
                    aria-label="Select a tool ontology to filter by"
                    size="sm">
                    <template v-slot:button-content>
                        <span class="sr-only">Select a tool ontology to filter by</span>
                        <FontAwesomeIcon :icon="faSitemap" />
                        <span v-if="selectedOntology">
                            {{ selectedOntology.name }}
                        </span>
                        <i v-else> Select an ontology to filter by </i>
                    </template>

                    <BDropdownGroup
                        id="searchable-sections"
                        class="sections-select-list"
                        header-classes="search-header">
                        <template v-slot:header>
                            <BDropdownText>
                                <BFormInput v-model="ontologiesFilter" type="text" placeholder="Filter ontologies..." />
                            </BDropdownText>
                        </template>

                        <BDropdownGroup
                            v-if="Object.keys(edamOperations).length"
                            id="edam-operations"
                            class="unselectable">
                            <template v-slot:header>
                                <FontAwesomeIcon
                                    v-if="getPanelIcon('ontology:edam_operations')"
                                    :icon="getPanelIcon('ontology:edam_operations')"
                                    fixed-width
                                    size="sm" />
                                <small class="font-weight-bold">{{ panels["ontology:edam_operations"]?.name }}</small>
                            </template>
                            <BDropdownItem
                                v-for="ont in edamOperations"
                                :key="ont.id"
                                :title="ont.description"
                                :active="selectedOntology?.id === ont.id"
                                @click="applyQuotedFilter('ontology', ont.id)">
                                <span v-localize>{{ ont.name }}</span>
                            </BDropdownItem>
                        </BDropdownGroup>

                        <BDropdownDivider />

                        <BDropdownGroup v-if="Object.keys(edamTopics).length" id="edam-topics" class="unselectable">
                            <template v-slot:header>
                                <FontAwesomeIcon
                                    v-if="getPanelIcon('ontology:edam_topics')"
                                    :icon="getPanelIcon('ontology:edam_topics')"
                                    fixed-width
                                    size="sm" />
                                <small class="font-weight-bold">{{ panels["ontology:edam_topics"]?.name }}</small>
                            </template>
                            <BDropdownItem
                                v-for="ont in edamTopics"
                                :key="ont.id"
                                :title="ont.description"
                                :active="selectedOntology?.id === ont.id"
                                @click="applyQuotedFilter('ontology', ont.id)">
                                <span v-localize>{{ ont.name }}</span>
                            </BDropdownItem>
                        </BDropdownGroup>
                    </BDropdownGroup>
                </BDropdown>

                <GButton
                    v-if="selectedOntology"
                    title="Remove ontology filter"
                    icon-only
                    inline
                    transparent
                    tooltip
                    @click="applyQuotedFilter('ontology', selectedOntology.id)">
                    <FontAwesomeIcon :icon="faTimes" />
                </GButton>
            </div>

            <slot name="list-view-controls" />
        </div>

        <ToolOntologyCard v-if="selectedOntology?.description" :ontology="selectedOntology" header />
    </div>
</template>

<style lang="scss" scoped>
.tool-section-dropdown {
    :deep(.dropdown-menu) {
        min-width: 100%;

        .search-header {
            padding: 0 0 0.5rem 0;
        }
        .sections-select-list > .list-unstyled {
            overflow-y: auto;
            max-height: 50vh;
        }
    }
}
</style>

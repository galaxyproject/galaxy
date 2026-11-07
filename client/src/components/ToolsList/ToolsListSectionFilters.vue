<script setup lang="ts">
import { faSitemap, type IconDefinition } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";

import type { FavoriteObjectKind } from "@/composables/useFavoriteObjects";
import { type ToolSection, useToolStore } from "@/stores/toolStore";
import type Filtering from "@/utils/filtering";

import { types_to_icons } from "../Panels/utilities";

import ToolFilterChip from "./ToolFilterChip.vue";
import ToolOntologyCard from "./ToolOntologyCard.vue";
import GFormInput from "@/components/BaseComponents/Form/GFormInput.vue";
import GDropdown from "@/components/BaseComponents/GDropdown.vue";
import GDropdownDivider from "@/components/BaseComponents/GDropdownDivider.vue";
import GDropdownGroup from "@/components/BaseComponents/GDropdownGroup.vue";
import GDropdownItem from "@/components/BaseComponents/GDropdownItem.vue";
import GDropdownText from "@/components/BaseComponents/GDropdownText.vue";

const props = defineProps<{
    /** The `Filtering` class (ToolFilters). */
    filterClass: Filtering<string | string[]>;
    /** The current filter text. */
    filterText: string;
    /** Whether the dropdowns should be disabled. */
    disabled?: boolean;
}>();

const emit = defineEmits<{
    (e: "apply-filter", filter: string, value: string): void;
}>();

const toolStore = useToolStore();
const { panels, panelSections } = storeToRefs(toolStore);

const ontologiesFilter = ref("");
const edamOperations = computed(() =>
    searchWithinSections(panelSections.value("ontology:edam_operations"), ontologiesFilter.value),
);
const edamTopics = computed(() =>
    searchWithinSections(panelSections.value("ontology:edam_topics"), ontologiesFilter.value),
);

const selectedOntology = computed<ToolSection | null>(() => {
    const ontologyValue = props.filterClass.getFilterValue(props.filterText, "ontology");
    const ontologyId = typeof ontologyValue === "string" ? ontologyValue.replace(/^"(.*)"$/, "$1") : undefined;
    return (
        toolStore.panelSections("ontology:edam_operations").find((section: ToolSection) => section.id === ontologyId) ||
        toolStore.panelSections("ontology:edam_topics").find((section: ToolSection) => section.id === ontologyId) ||
        (ontologyId ? { id: ontologyId, name: ontologyId, model_class: "ToolSection" } : null)
    );
});

/** Ensures `toolStore.toolSections` contains the ontology sections used in this view. */
async function ensureOntologiesLoaded() {
    await toolStore.fetchToolSections("ontology:edam_operations");
    await toolStore.fetchToolSections("ontology:edam_topics");
}
ensureOntologiesLoaded();

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

/** Only EDAM ids can be favorited; other ontology filter values are just removable */
function ontologyFavoriteKind(ontologyId: string): FavoriteObjectKind | undefined {
    if (/^operation_\d+$/.test(ontologyId)) {
        return "edam_operations";
    }
    if (/^topic_\d+$/.test(ontologyId)) {
        return "edam_topics";
    }
    return undefined;
}
</script>

<template>
    <div class="d-flex flex-column flex-gapy-1">
        <div class="d-flex flex-wrap justify-content-between align-items-center flex-gapx-1 flex-gapy-1">
            <div class="d-flex flex-wrap flex-grow-1 align-items-center flex-gapx-1 flex-gapy-1">
                <slot name="tag-filter" />

                <div class="d-flex align-items-center flex-gapx-1">
                    <GDropdown
                        block
                        :disabled="props.disabled"
                        variant="link"
                        class="tool-section-dropdown"
                        initial-focus="input"
                        toggle-class="text-decoration-none"
                        size="sm">
                        <template v-slot:button-content>
                            <span class="sr-only">Select a tool ontology to filter by</span>
                            <FontAwesomeIcon :icon="faSitemap" />
                            <i> Select an ontology to filter by </i>
                        </template>

                        <GDropdownGroup
                            id="searchable-sections"
                            class="sections-select-list"
                            header-classes="search-header"
                            aria-label="Ontologies">
                            <template v-slot:header>
                                <GDropdownText>
                                    <GFormInput
                                        v-model="ontologiesFilter"
                                        class="w-100"
                                        aria-label="Search ontologies"
                                        type="text"
                                        placeholder="Filter ontologies..." />
                                </GDropdownText>
                            </template>

                            <GDropdownGroup
                                v-if="Object.keys(edamOperations).length"
                                id="edam-operations"
                                class="unselectable"
                                :aria-label="panels['ontology:edam_operations']?.name">
                                <template v-slot:header>
                                    <FontAwesomeIcon
                                        v-if="getPanelIcon('ontology:edam_operations')"
                                        :icon="getPanelIcon('ontology:edam_operations')!"
                                        fixed-width
                                        size="sm" />
                                    <small class="font-weight-bold">{{
                                        panels["ontology:edam_operations"]?.name
                                    }}</small>
                                </template>
                                <GDropdownItem
                                    v-for="ont in edamOperations"
                                    :key="ont.id"
                                    :title="ont.description"
                                    :active="selectedOntology?.id === ont.id"
                                    @click="applyQuotedFilter('ontology', ont.id)">
                                    <span v-localize>{{ ont.name }}</span>
                                </GDropdownItem>
                            </GDropdownGroup>

                            <GDropdownDivider />

                            <GDropdownGroup
                                v-if="Object.keys(edamTopics).length"
                                id="edam-topics"
                                class="unselectable"
                                :aria-label="panels['ontology:edam_topics']?.name">
                                <template v-slot:header>
                                    <FontAwesomeIcon
                                        v-if="getPanelIcon('ontology:edam_topics')"
                                        :icon="getPanelIcon('ontology:edam_topics')!"
                                        fixed-width
                                        size="sm" />
                                    <small class="font-weight-bold">{{ panels["ontology:edam_topics"]?.name }}</small>
                                </template>
                                <GDropdownItem
                                    v-for="ont in edamTopics"
                                    :key="ont.id"
                                    :title="ont.description"
                                    :active="selectedOntology?.id === ont.id"
                                    @click="applyQuotedFilter('ontology', ont.id)">
                                    <span v-localize>{{ ont.name }}</span>
                                </GDropdownItem>
                            </GDropdownGroup>
                        </GDropdownGroup>
                    </GDropdown>

                    <ToolFilterChip
                        v-if="selectedOntology"
                        :label="selectedOntology.name"
                        :value="selectedOntology.id"
                        :kind="ontologyFavoriteKind(selectedOntology.id)"
                        :remove-title="`Remove ontology ${selectedOntology.name}`"
                        :disabled="props.disabled"
                        @remove="applyQuotedFilter('ontology', selectedOntology.id)" />
                </div>
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

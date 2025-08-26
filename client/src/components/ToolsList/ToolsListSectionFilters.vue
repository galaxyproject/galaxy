<script setup lang="ts">
import {
    faExternalLinkAlt,
    faLayerGroup,
    faLink,
    faSitemap,
    type IconDefinition,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BDropdown, BDropdownDivider, BDropdownGroup, BDropdownItem, BDropdownText, BFormInput } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref, watch } from "vue";

import { getFullAppUrl } from "@/app/utils";
import { Toast } from "@/composables/toast";
import { type ToolSection, useToolStore } from "@/stores/toolStore";
import { copy } from "@/utils/clipboard";
import type Filtering from "@/utils/filtering";

import type { CardAction } from "../Common/GCard.types";
import { types_to_icons } from "../Panels/utilities";

import GCard from "../Common/GCard.vue";

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
const { defaultPanelView, panels } = storeToRefs(toolStore);

const defaultToolSectionsFilter = ref("");
const defaultToolSections = computed(() =>
    toolStore.getToolSections(defaultPanelView.value, defaultToolSectionsFilter.value),
);

const ontologiesFilter = ref("");
const edamOperations = computed(() => toolStore.getToolSections("ontology:edam_operations", ontologiesFilter.value));
const edamTopics = computed(() => toolStore.getToolSections("ontology:edam_topics", ontologiesFilter.value));

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

const selectedOntologyActions = computed<CardAction[]>(() => {
    const actions: CardAction[] = [];
    if (selectedOntology.value) {
        const ontologyId = selectedOntology.value.id;
        const ontologyName = selectedOntology.value.name;
        actions.push({
            id: "tools-list-ontology-filter-link",
            label: "Link to these results",
            icon: faLink,
            title: "Copy link to these results",
            variant: "outline-primary",
            handler: () => {
                const link = getFullAppUrl(`tools/list?ontology="${ontologyId}"`);
                copy(link);
                Toast.success(`Link to ontology "${ontologyName} (${ontologyId})" copied to clipboard`);
            },
        });
        if (selectedOntology.value.links && "edam_browser" in selectedOntology.value.links) {
            actions.push({
                id: "ontology-link",
                label: "EDAM Browser",
                icon: faExternalLinkAlt,
                title: "View in EDAM Browser",
                variant: "outline-primary",
                href: selectedOntology.value.links.edam_browser,
                externalLink: true,
            });
        }
    }
    return actions;
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
</script>

<template>
    <div class="d-flex flex-column flex-gapy-1">
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

                <BDropdownGroup id="searchable-sections" class="sections-select-list" header-classes="search-header">
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

                <BDropdownGroup id="searchable-sections" class="sections-select-list" header-classes="search-header">
                    <template v-slot:header>
                        <BDropdownText>
                            <BFormInput v-model="ontologiesFilter" type="text" placeholder="Filter ontologies..." />
                        </BDropdownText>
                    </template>

                    <BDropdownGroup v-if="Object.keys(edamOperations).length" id="edam-operations" class="unselectable">
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
        </div>

        <GCard
            v-if="selectedOntology?.description"
            current
            :badges="[
                {
                    id: 'ontology-id',
                    label: selectedOntology.id,
                    title: 'The EDAM id for this ontology',
                    class: 'ontology-badge',
                    visible: true,
                    icon: faSitemap,
                },
            ]"
            :secondary-actions="selectedOntologyActions"
            :description="selectedOntology.description"
            full-description
            :title="selectedOntology.name">
            <template v-slot:update-time>
                <i v-if="selectedOntology.tools">
                    {{ selectedOntology.tools.length }} tools in this ontology

                    <!-- TODO: There can be a mismatch here, maybe try to fix. Something like this looks better:
                    {{ Math.max(selectedOntology.tools.length, itemsLoaded.length) }} tools in this ontology -->
                </i>
            </template>
        </GCard>
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

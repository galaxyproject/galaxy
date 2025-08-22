<script setup lang="ts">
import type { IconDefinition } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BDropdown, BDropdownDivider, BDropdownGroup, BDropdownItem } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed } from "vue";

import { type ToolSection, useToolStore } from "@/stores/toolStore";
import type Filtering from "@/utils/filtering";

import { types_to_icons } from "../Panels/utilities";

import GLink from "../BaseComponents/GLink.vue";
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

const defaultToolSections = computed(() => toolStore.getToolSections(defaultPanelView.value));

const edamOperations = computed(() => toolStore.getToolSections("ontology:edam_operations"));
const edamTopics = computed(() => toolStore.getToolSections("ontology:edam_topics"));

const selectedSection = computed<ToolSection | null>(() => {
    const sectionName = props.filterClass.getFilterValue(props.filterText, "section");
    return (
        Object.values(defaultToolSections.value).find((section: ToolSection) => section.name === sectionName) || null
    );
});

const selectedOntology = computed<ToolSection | null>(() => {
    const ontologyId = props.filterClass.getFilterValue(props.filterText, "ontology");
    return (
        Object.values(edamOperations.value).find((section: ToolSection) => section.id === ontologyId) ||
        Object.values(edamTopics.value).find((section: ToolSection) => section.id === ontologyId) ||
        null
    );
});

ensureSectionsAndOntologiesLoaded();

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
                    <span v-if="selectedSection">
                        {{ selectedSection.name }}
                    </span>
                    <i v-else> Select a section to filter by </i>
                </template>

                <BDropdownItem
                    v-for="sec in defaultToolSections"
                    :key="sec.id"
                    :title="sec.description"
                    :active="selectedSection?.id === sec.id"
                    @click="emit('apply-filter', 'section', sec.name)">
                    <span v-localize>{{ sec.name }}</span>
                </BDropdownItem>
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
                    <span v-if="selectedOntology">
                        {{ selectedOntology.name }}
                    </span>
                    <i v-else> Select an ontology to filter by </i>
                </template>

                <BDropdownGroup id="edam-operations" class="unselectable">
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
                        @click="emit('apply-filter', 'ontology', ont.id)">
                        <span v-localize>{{ ont.name }}</span>
                    </BDropdownItem>
                </BDropdownGroup>

                <BDropdownDivider />

                <BDropdownGroup id="edam-topics" class="unselectable">
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
                        @click="emit('apply-filter', 'ontology', ont.id)">
                        <span v-localize>{{ ont.name }}</span>
                    </BDropdownItem>
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
                },
            ]"
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
            <template v-slot:secondary-actions>
                <div v-if="selectedOntology.links && Object.keys(selectedOntology.links).length > 0">
                    <GLink
                        v-for="(link, key) in selectedOntology.links"
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
</template>

<style lang="scss" scoped>
.tool-section-dropdown {
    :deep(.dropdown-menu) {
        overflow: auto;
        max-height: 50vh;
        min-width: 100%;
    }
}
</style>

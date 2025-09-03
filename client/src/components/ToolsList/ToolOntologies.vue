<script setup lang="ts">
import { faExternalLinkAlt, faFilter, faSortAlphaDown, faSortAlphaUp } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BBadge, BDropdown, BDropdownItem, BFormInput } from "bootstrap-vue";
import { computed, ref, watch } from "vue";

import { type ToolSection, useToolStore } from "@/stores/toolStore";
import { errorMessageAsString } from "@/utils/simple-error";

import { searchSections } from "../Panels/utilities";

import ToolOntologyCard from "./ToolOntologyCard.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
import BreadcrumbHeading from "@/components/Common/BreadcrumbHeading.vue";
import HelpText from "@/components/Help/HelpText.vue";
import ScrollList from "@/components/ScrollList/ScrollList.vue";

const toolStore = useToolStore();

const ontologiesFilter = ref("");
const loading = ref(true);
const errorMessage = ref("");

const showing = ref<"operations" | "topics" | "all">("all");
const sortOrder = ref<"asc" | "desc">("asc");

const currentOffset = ref(0);

const breadcrumbItems = computed(() => [
    { title: "Discover Tools", to: "/tools/list" },
    { title: "EDAM Ontologies", to: "/tools/list/ontologies" },
]);

const validFilter = computed(() =>
    ontologiesFilter.value.trim().length >= 3 ? ontologiesFilter.value.trim() : undefined,
);
const edamOperations = computed(() => toolStore.panelSections("ontology:edam_operations"));
const edamTopics = computed(() => toolStore.panelSections("ontology:edam_topics"));

const filtered = computed<{
    sections: ToolSection[];
    closestTerm: string | null;
}>(() => {
    let ontologies;
    switch (showing.value) {
        case "topics":
            ontologies = Object.values(edamTopics.value);
            break;
        case "operations":
            ontologies = Object.values(edamOperations.value);
            break;
        default:
            ontologies = Object.values(edamOperations.value).concat(Object.values(edamTopics.value));
    }

    if (validFilter.value) {
        return searchSections(ontologies, validFilter.value);
    }

    const sorted = [...ontologies].sort((a, b) => {
        const nameA = a.name?.toLowerCase() ?? "";
        const nameB = b.name?.toLowerCase() ?? "";
        if (nameA < nameB) {
            return sortOrder.value === "asc" ? -1 : 1;
        }
        if (nameA > nameB) {
            return sortOrder.value === "asc" ? 1 : -1;
        }
        return 0;
    });
    return { sections: sorted, closestTerm: null };
});

const shownOntologies = computed(() => filtered.value.sections.slice(0, currentOffset.value));

const ontologyDatalist = computed(() => {
    switch (showing.value) {
        case "topics":
            return toolStore.sectionDatalist("ontology:edam_topics");
        case "operations":
            return toolStore.sectionDatalist("ontology:edam_operations");
        default:
            return toolStore
                .sectionDatalist("ontology:edam_topics")
                .concat(toolStore.sectionDatalist("ontology:edam_operations"));
    }
});

ensureOntologiesLoaded();

/** Ensures the two EDAM ontology tool panel views are in the store.
 *
 * _Note that the `toolStore` itself ensures a panel isn't loaded if it's already present in the state._
 */
async function ensureOntologiesLoaded() {
    try {
        await toolStore.fetchToolSections("ontology:edam_operations");
        await toolStore.fetchToolSections("ontology:edam_topics");
    } catch (error) {
        errorMessage.value = errorMessageAsString(error);
    } finally {
        loading.value = false;
    }
}

function changeSort() {
    if (sortOrder.value === "asc") {
        sortOrder.value = "desc";
    } else {
        sortOrder.value = "asc";
    }
}

/** Since we can have a massive list of ontologies, we use this method to paginate */
async function loadMore(_: number, limit: number) {
    currentOffset.value += limit;

    return { items: shownOntologies.value, total: filtered.value.sections.length };
}

// As these variables change, reset the current offset to show first 20 results
watch([ontologiesFilter, sortOrder, showing], async () => {
    currentOffset.value = 20;
});
</script>

<template>
    <div class="d-flex flex-column">
        <div class="d-flex flex-column flex-gapy-1 mb-2">
            <BreadcrumbHeading :items="breadcrumbItems" />

            <BFormInput
                v-model="ontologiesFilter"
                type="text"
                placeholder="Filter ontologies"
                list="ontology-list-datalist" />
            <datalist v-if="ontologyDatalist.length" id="ontology-list-datalist">
                <option v-for="data in ontologyDatalist" :key="data.value" :label="data.text" :value="data.text" />
            </datalist>

            <BBadge v-if="ontologiesFilter.trim() && !validFilter" class="alert-info w-100">
                Search term is too short
            </BBadge>

            <BBadge v-else-if="filtered.closestTerm" class="alert-danger w-100">
                Did you mean:
                <i>
                    <a href="javascript:void(0)" @click="ontologiesFilter = filtered.closestTerm">
                        {{ filtered.closestTerm }}
                    </a>
                </i>
                ?
            </BBadge>

            <div class="d-flex justify-content-between align-items-center tool-ontologies-header">
                <div class="d-flex flex-gapx-1 align-items-center">
                    <HelpText uri="galaxy.tools.ontologies.description" text="What are EDAM Ontologies?" />

                    <GButton transparent href="https://edamontology.org/" target="_blank" inline icon-only>
                        <FontAwesomeIcon :icon="faExternalLinkAlt" />
                    </GButton>
                </div>

                <div class="d-flex flex-gapx-1 align-items-center">
                    <BBadge class="edam-ontology-badge topic text-left" pill>
                        <HelpText uri="galaxy.tools.ontologies.topic" text="What is an EDAM Topic?" />
                    </BBadge>
                    <BBadge class="edam-ontology-badge operation text-left" pill>
                        <HelpText uri="galaxy.tools.ontologies.operation" text="What is an EDAM Operation?" />
                    </BBadge>

                    <BDropdown
                        block
                        :disabled="loading"
                        variant="link"
                        toggle-class="text-decoration-none"
                        role="menu"
                        aria-label="Choose whether to show operations, topics, or all"
                        size="sm">
                        <template v-slot:button-content>
                            <span class="sr-only">Choose whether to show operations, topics, or all</span>
                            <FontAwesomeIcon :icon="faFilter" />
                            <i v-if="showing === 'all'">Showing all Ontologies</i>
                            <span v-else-if="showing === 'topics'">Showing Topics Only</span>
                            <span v-else>Showing Operations Only</span>
                        </template>

                        <BDropdownItem @click="showing = 'all'">Show All Ontologies</BDropdownItem>
                        <BDropdownItem @click="showing = 'operations'">Show Operations Only</BDropdownItem>
                        <BDropdownItem @click="showing = 'topics'">Show Topics Only</BDropdownItem>
                    </BDropdown>

                    <GButton v-if="!validFilter" color="blue" outline @click="changeSort">
                        <FontAwesomeIcon :icon="sortOrder === 'asc' ? faSortAlphaDown : faSortAlphaUp" />
                        Sort
                    </GButton>
                </div>
            </div>
        </div>

        <BAlert v-if="errorMessage" show variant="danger">
            {{ errorMessage }}
        </BAlert>

        <div class="d-flex flex-column overflow-auto h-100">
            <ScrollList
                ref="root"
                :loader="loadMore"
                :item-key="(tool) => tool.id"
                :prop-items="shownOntologies"
                :prop-total-count="filtered.sections.length"
                :prop-busy="loading"
                name="ontology"
                name-plural="ontologies"
                :scroll-top-reset-key="`${ontologiesFilter}-${showing}-${sortOrder}`"
                show-count-in-footer>
                <template v-slot:item="{ item }">
                    <ToolOntologyCard :key="item.id" :ontology="item" routable />
                </template>
            </ScrollList>
        </div>
    </div>
</template>

<style lang="scss" scoped>
.tool-ontologies-header {
    :deep(.popper-element) {
        max-width: 70vw;
    }

    .edam-ontology-badge {
        white-space: normal !important;
    }
}
</style>

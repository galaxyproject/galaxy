<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faAngleDoubleDown, faAngleDoubleUp, faRedo, faSearch } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, BFormInput, BInputGroup, BInputGroupAppend } from "bootstrap-vue";
import { computed, ref } from "vue";

import Filtering, { type HandlerReturn } from "@/utils/filtering";

import AdvancedFilteringHelpModal from "@/components/Common/AdvancedFilteringHelpModal.vue";

library.add(faAngleDoubleDown, faAngleDoubleUp, faRedo, faSearch);

type FilterOption = {
    filter: string;
    description: string;
};

interface Props {
    helpTitle?: string;
    advancedMode?: boolean;
    useDefaults?: boolean;
    searchPlaceHolder: string;
    filterOptions: FilterOption[];
    advancedFilterFields?: string[];
    validFilters: Record<string, HandlerReturn<unknown>>;
}

const props = withDefaults(defineProps<Props>(), {
    helpTitle: "",
    useDefaults: false,
    advancedMode: false,
    searchPlaceHolder: "Search",
    advancedFilterFields: () => ["name", "tag"],
});

const filters = new Filtering(props.validFilters, props.useDefaults);

const filterText = ref("");
const showHelp = ref(false);
const showAdvanced = ref(false);

const filterSettings = computed(() => filters.toAlias(filters.getFiltersForText(filterText.value)));
const localFilter = computed({
    get() {
        return filterText.value;
    },
    set(newVal: string) {
        if (newVal !== filterText.value) {
            updateFilter(newVal);
        }
    },
});

function updateFilter(newVal: string) {
    filterText.value = newVal.trim();
}

function onToggle() {
    showAdvanced.value = !showAdvanced.value;
}

function onToggleHelp() {
    showHelp.value = !showHelp.value;
}

function onSearch() {
    onToggle();
    updateFilter(filters.getFilterText(filterSettings.value));
}

defineExpose({
    filters,
    filterText,
    updateFilter,
});
</script>

<template>
    <div>
        <BInputGroup class="mb-2">
            <BFormInput
                id="filter-input"
                v-model="localFilter"
                debounce="500"
                size="sm"
                :class="filterText && 'font-weight-bold'"
                :placeholder="searchPlaceHolder"
                title="clear search (esc)"
                data-description="filter text input"
                @keyup.esc="updateFilter('')" />

            <BInputGroupAppend>
                <BButton
                    v-if="advancedMode"
                    v-b-tooltip.hover
                    size="sm"
                    aria-haspopup="true"
                    title="Advanced Filtering Help"
                    @click="onToggleHelp">
                    <FontAwesomeIcon icon="question" />
                </BButton>

                <BButton
                    v-if="advancedMode"
                    v-b-tooltip.hover
                    size="sm"
                    :title="showAdvanced ? 'Hide advanced filter' : 'Show advanced filter'"
                    :pressed="showAdvanced"
                    :variant="showAdvanced ? 'info' : 'secondary'"
                    @click="onToggle">
                    <FontAwesomeIcon :icon="showAdvanced ? faAngleDoubleUp : faAngleDoubleDown" />
                </BButton>

                <BButton v-b-tooltip.hover size="sm" title="Clear filters (esc)" @click="updateFilter('')">
                    <FontAwesomeIcon icon="times" />
                </BButton>
            </BInputGroupAppend>
        </BInputGroup>

        <div v-if="advancedMode && showAdvanced" fluid class="mb-2" @keyup.enter="onSearch">
            <div v-for="fieldName in advancedFilterFields" :key="fieldName">
                <small :for="`advanced-filter-${fieldName}`"> Filter by {{ fieldName }}: </small>
                <BFormInput
                    :id="`advanced-filter-${fieldName}`"
                    v-model="filterSettings[`${fieldName}:`]"
                    size="sm"
                    :placeholder="`any ${fieldName}`" />
            </div>

            <div class="my-2">
                <BButton size="sm" variant="primary" @click="onSearch">
                    <FontAwesomeIcon :icon="faSearch" />
                    Search
                </BButton>

                <BButton size="sm" variant="outline-primary" title="Close advanced filter" @click="onToggle">
                    <FontAwesomeIcon :icon="faRedo" />
                    Close
                </BButton>
            </div>
        </div>

        <AdvancedFilteringHelpModal
            v-if="advancedMode"
            :title="helpTitle"
            :visible="showHelp"
            :filter-options="filterOptions"
            @close="onToggleHelp" />
    </div>
</template>

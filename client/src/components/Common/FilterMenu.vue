<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faAngleDoubleUp, faQuestion, faRedo, faSearch } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, BModal } from "bootstrap-vue";
import { kebabCase } from "lodash";
import { computed, ref, watch } from "vue";

import type Filtering from "@/utils/filtering";
import { type Alias, getOperatorForAlias } from "@/utils/filtering";

import DelayedInput from "@/components/Common/DelayedInput.vue";
import FilterMenuBoolean from "@/components/Common/FilterMenuBoolean.vue";
import FilterMenuInput from "@/components/Common/FilterMenuInput.vue";
import FilterMenuMultiTags from "@/components/Common/FilterMenuMultiTags.vue";
import FilterMenuObjectStore from "@/components/Common/FilterMenuObjectStore.vue";
import FilterMenuQuotaSource from "@/components/Common/FilterMenuQuotaSource.vue";
import FilterMenuRanged from "@/components/Common/FilterMenuRanged.vue";

library.add(faAngleDoubleUp, faQuestion, faRedo, faSearch);

interface BackendFilterError {
    err_msg: string;
    err_code: number;
    column?: string;
    col?: string;
    operation?: Alias;
    op?: Alias;
    value?: string;
    val?: string;
    ValueError?: string;
}

interface Props {
    /** A name for the menu */
    name?: string;
    /** A placeholder for the main search input */
    placeholder?: string;
    /** The delay (in ms) before the main filter is applied */
    debounceDelay?: number;
    /** The `Filtering` class to use */
    filterClass: Filtering<any>;
    /** The current filter text in the main field */
    filterText?: string;
    /** Whether a help `<template>` has been provided for the `<slot>` */
    hasHelp?: boolean;
    /** Whether to replace default Cancel (toggle) button with Clear */
    hasClearBtn?: boolean;
    /** Triggers the loading icon */
    loading?: boolean;
    /** Default `linked`: filters react to current `filterText` */
    menuType?: "linked" | "separate" | "standalone";
    /** A `BackendFilterError` if provided */
    searchError?: BackendFilterError;
    /** Whether the advanced menu is currently expanded */
    showAdvanced?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    name: "Menu",
    placeholder: "search for items",
    debounceDelay: 500,
    filterText: "",
    menuType: "linked",
    showAdvanced: false,
    searchError: undefined,
});

const emit = defineEmits<{
    (e: "update:filter-text", filter: string): void;
    (e: "on-backend-filter", filter: string): void;
    (e: "update:show-advanced", showAdvanced: boolean): void;
    (e: "on-search", filters: Record<string, string | boolean>, filterText?: string, backendFilter?: string): void;
}>();

const validFilters = computed(() => props.filterClass.validFilters);

const filters = computed(() => Object.fromEntries(props.filterClass.getFiltersForText(props.filterText)));

const identifier = kebabCase(props.name);

// Boolean for showing the help modal for the whole filter menu (if provided)
const showHelp = ref(false);

const formattedSearchError = computed(() => {
    if (props.searchError) {
        const { column, col, operation, op, value, val, err_msg, ValueError } = props.searchError;
        const alias = operation || op;
        const operator = alias ? getOperatorForAlias(alias) : ":";
        const formatted = {
            filter: `${column || col}${operator}`,
            index: alias && alias !== "eq" ? `${column || col}_${alias}` : column || col,
            value: value || val,
            msg: err_msg,
            typeError: ValueError,
        };
        return formatted;
    } else {
        return null;
    }
});

/** Explicitly sets a filter: value
 * (also closes help modal for this filter if it exists)
 * @param filter the filter to set
 * @param value the value to set it to
 */
function onOption(filter: string, value: any) {
    filters.value[filter] = value;
}

function onSearch() {
    const newFilterText = props.filterClass.getFilterText(filters.value);
    const newBackendFilter = props.filterClass.getFilterText(filters.value, true);
    if (props.menuType !== "linked") {
        emit("on-search", filters.value, newFilterText, newBackendFilter);
    } else {
        updateFilterText(newFilterText);
        onToggle();
    }
}

function onToggle() {
    emit("update:show-advanced", !props.showAdvanced);
}

function updateFilterText(newFilterText: string) {
    emit("update:filter-text", newFilterText);
}

// as the filterText changes, emit a backend-filter that can be used as a backend query
watch(
    () => props.filterText,
    (newFilterText: string) => {
        const defaultBackendFilter = props.filterClass.getFilterText(props.filterClass.defaultFilters, true);
        const currentBackendFilter = props.filterClass.getFilterText(filters.value, true);

        const backendFilter =
            defaultBackendFilter === currentBackendFilter
                ? `${
                      defaultBackendFilter && !newFilterText.includes(defaultBackendFilter)
                          ? defaultBackendFilter + " "
                          : ""
                  }` + newFilterText
                : props.filterClass.getFilterText(filters.value, true);
        emit("on-backend-filter", backendFilter);
    }
);
</script>

<template>
    <div>
        <DelayedInput
            v-if="props.menuType !== 'standalone'"
            v-show="props.menuType == 'linked' || (props.menuType == 'separate' && !props.showAdvanced)"
            :query="props.filterText"
            :delay="props.debounceDelay"
            :loading="props.loading"
            :show-advanced="props.showAdvanced"
            enable-advanced
            :placeholder="props.placeholder"
            @change="updateFilterText"
            @onToggle="onToggle" />

        <BButton
            v-if="props.menuType == 'separate' && props.showAdvanced"
            v-b-tooltip.hover.bottom.noninteractive
            class="w-100"
            aria-haspopup="true"
            size="sm"
            :pressed="props.showAdvanced"
            title="Toggle Advanced Search"
            data-description="wide toggle advanced search"
            @click="onToggle">
            <FontAwesomeIcon fixed-width :icon="faAngleDoubleUp" />
        </BButton>

        <div
            v-if="props.menuType == 'standalone' || props.showAdvanced"
            class="mt-2"
            data-description="advanced filters">
            <div v-for="filter in Object.keys(validFilters)" :key="filter">
                <span v-if="validFilters[filter]?.menuItem">
                    <FilterMenuBoolean
                        v-if="validFilters[filter]?.type == Boolean"
                        :name="filter"
                        :filter="validFilters[filter]"
                        :filters="filters"
                        @change="onOption"
                        @on-enter="onSearch"
                        @on-esc="onToggle" />
                    <FilterMenuRanged
                        v-else-if="validFilters[filter]?.isRangeInput"
                        class="m-0"
                        :name="filter"
                        :filter="validFilters[filter]"
                        :filters="filters"
                        :error="formattedSearchError"
                        :identifier="identifier"
                        @change="onOption"
                        @on-enter="onSearch"
                        @on-esc="onToggle" />
                    <FilterMenuMultiTags
                        v-else-if="validFilters[filter]?.type == 'MultiTags'"
                        :name="filter"
                        :filter="validFilters[filter]"
                        :filters="filters"
                        :identifier="identifier"
                        @change="onOption" />
                    <FilterMenuObjectStore
                        v-else-if="validFilters[filter]?.type == 'ObjectStore'"
                        :name="filter"
                        :filter="validFilters[filter]"
                        :filters="filters"
                        @change="onOption" />
                    <FilterMenuQuotaSource
                        v-else-if="validFilters[filter]?.type == 'QuotaSource'"
                        :name="filter"
                        :filter="validFilters[filter]"
                        :filters="filters"
                        :identifier="identifier"
                        @change="onOption" />
                    <FilterMenuInput
                        v-else
                        :name="filter"
                        :filter="validFilters[filter]"
                        :filters="filters"
                        :error="formattedSearchError"
                        :identifier="identifier"
                        @change="onOption"
                        @on-enter="onSearch"
                        @on-esc="onToggle" />
                </span>
            </div>

            <!-- Perform search or cancel out (or open help modal for whole Menu if exists) -->
            <div class="mb-3 mt-1">
                <BButton
                    :id="`${identifier}-advanced-filter-submit`"
                    class="mr-1"
                    size="sm"
                    variant="primary"
                    data-description="apply filters"
                    @click="onSearch">
                    <FontAwesomeIcon :icon="faSearch" />

                    <span v-localize>Search</span>
                </BButton>

                <BButton v-if="props.menuType !== 'standalone'" size="sm" @click="onToggle">
                    <FontAwesomeIcon :icon="faRedo" />

                    <span v-localize>Cancel</span>
                </BButton>

                <BButton v-if="props.hasHelp" title="Search Help" size="sm" @click="showHelp = true">
                    <FontAwesomeIcon :icon="faQuestion" />
                </BButton>

                <span> </span>

                <BModal v-if="props.hasHelp" v-model="showHelp" :title="`${props.name} Advanced Search Help`" ok-only>
                    <!-- Slot for Menu help section -->
                    <slot name="menu-help-text"></slot>
                </BModal>
            </div>
        </div>
    </div>
</template>

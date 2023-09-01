<script setup lang="ts">
import { capitalize, kebabCase } from "lodash";
import { computed, type Ref, ref, watch } from "vue";

import type Filtering from "@/utils/filtering";
import { type Alias, getOperatorForAlias } from "@/utils/filtering";

import DelayedInput from "@/components/Common/DelayedInput.vue";
import FilterMenuBoolean from "@/components/Common/FilterMenuBoolean.vue";
import StatelessTags from "@/components/TagsMultiselect/StatelessTags.vue";

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

const props = withDefaults(
    defineProps<{
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
    }>(),
    {
        name: "Menu",
        placeholder: "search for items",
        debounceDelay: 500,
        filterText: "",
        menuType: "linked",
        showAdvanced: false,
        searchError: undefined,
    }
);

const emit = defineEmits<{
    (e: "update:filter-text", filter: string): void;
    (e: "on-backend-filter", filter: string): void;
    (e: "update:show-advanced", showAdvanced: boolean): void;
    (e: "on-search", filters: Record<string, string | boolean>, filterText?: string, backendFilter?: string): void;
}>();

const validFilters = computed(() => props.filterClass.validFilters);

const filters = computed(() => Object.fromEntries(props.filterClass.getFiltersForText(props.filterText)));

const identifier = kebabCase(props.name);

// all filters that have help info
const helpKeys = Object.keys(validFilters.value).filter((key) => validFilters.value[key]?.helpInfo !== undefined);
const defaultHelpModalsVal = helpKeys.reduce((acc: { [k: string]: boolean }, item: string) => {
    acc[item] = false;
    return acc;
}, {});
/**
 * An object of booleans that are used to show/hide the help modals for
 * each filter that has them
 */
const helpModals: Ref<{ [k: string]: boolean }> = ref({ ...defaultHelpModalsVal });

// Boolean for showing the help modal for the whole filter menu (if provided)
const showHelp = ref(false);

/**
 * Reactively storing and getting all filters from validFilters which are `.type == Date`
 * and .type == 'MultiTags'
 * (This was done to make the datepickers and tags store values in the `filters` object)
 */
const dateFilters: Ref<{ [key: string]: string }> = ref({});
const dateKeys = Object.keys(validFilters.value).filter((key) => validFilters.value[key]?.type == Date);
dateKeys.forEach((key: string) => {
    if (validFilters.value[key]?.isRangeInput) {
        dateKeys.push(key + "_lt");
        dateKeys.push(key + "_gt");
    }
});
const multiTagFilters: Ref<{ [key: string]: Ref<string[]> }> = ref({});
const multiTagKeys = Object.keys(validFilters.value).filter((key) => validFilters.value[key]?.type == "MultiTags");
multiTagKeys.forEach((key: string) => {
    if (filters.value[key] !== undefined) {
        multiTagFilters.value[key] = ref(filters.value[key] as string[]);
    } else {
        multiTagFilters.value[key] = ref([]);
    }
});
watch(
    () => filters.value,
    (newFilters: { [k: string]: any }) => {
        dateKeys.forEach((key: string) => {
            if (newFilters[key]) {
                dateFilters.value[key] = newFilters[key] as string;
            } else {
                delete dateFilters.value[key];
            }
        });
        multiTagKeys.forEach((key: string) => {
            if (newFilters[key]) {
                (multiTagFilters.value[key] as Ref<string[]>).value = newFilters[key];
            } else {
                (multiTagFilters.value[key] as Ref<string[]>).value = [];
            }
        });
    }
);

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

function hasError(field: string) {
    if (formattedSearchError.value && formattedSearchError.value.index == field) {
        return formattedSearchError.value.typeError || formattedSearchError.value.msg;
    }
    return "";
}

/** Explicitly sets a filter: value
 * (also closes help modal for this filter if it exists)
 * @param filter the filter to set
 * @param value the value to set it to
 */
function onOption(filter: string, value: any) {
    filters.value[filter] = value;
    if (helpModals.value[filter]) {
        helpModals.value[filter] = false;
    }
}

function onSearch() {
    Object.keys(dateFilters.value).forEach((key) => {
        onOption(key, dateFilters.value[key]);
    });
    Object.keys(multiTagFilters.value).forEach((key) => {
        onOption(key, (multiTagFilters.value[key] as Ref<string[]>).value);
    });
    const newFilterText = props.filterClass.getFilterText(filters.value);
    const newBackendFilter = props.filterClass.getFilterText(filters.value, true);
    if (props.menuType !== "linked") {
        emit("on-search", filters.value, newFilterText, newBackendFilter);
    } else {
        updateFilterText(newFilterText);
        onToggle();
    }
}

function onTags(filter: string, tags: string[]) {
    (multiTagFilters.value[filter] as Ref<string[]>).value = tags;
}

function onToggle() {
    emit("update:show-advanced", !props.showAdvanced);
}

function updateFilterText(newFilterText: string) {
    emit("update:filter-text", newFilterText);
}

// as the filterText changes, emit a backend-filter that can be used as a query
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
            :class="props.filterText && 'font-weight-bold'"
            :query="props.filterText"
            :delay="props.debounceDelay"
            :loading="props.loading"
            :show-advanced="props.showAdvanced"
            enable-advanced
            :placeholder="props.placeholder"
            @change="updateFilterText"
            @onToggle="onToggle" />
        <b-button
            v-if="props.menuType == 'separate' && props.showAdvanced"
            v-b-tooltip.hover.noninteractive
            class="w-100"
            aria-haspopup="true"
            size="sm"
            :pressed="props.showAdvanced"
            title="Toggle Advanced Search"
            data-description="wide toggle advanced search"
            @click="onToggle">
            <icon fixed-width icon="angle-double-up" />
        </b-button>
        <div
            v-if="props.menuType == 'standalone' || props.showAdvanced"
            class="mt-2"
            data-description="advanced filters"
            @keyup.enter="onSearch"
            @keyup.esc="onToggle">
            <div v-for="filter in Object.keys(validFilters)" :key="filter">
                <span v-if="validFilters[filter]?.menuItem">
                    <!-- is a Boolean filter -->
                    <span v-if="validFilters[filter]?.type == Boolean">
                        <small>{{ validFilters[filter]?.placeholder }}:</small>
                        <FilterMenuBoolean
                            :name="filter"
                            :filter="validFilters[filter]"
                            :settings="filters"
                            @change="onOption" />
                    </span>

                    <!-- is a Ranged filter -->
                    <span v-else-if="validFilters[filter]?.isRangeInput" class="m-0">
                        <small>Filter by {{ validFilters[filter]?.placeholder }}:</small>
                        <b-input-group>
                            <!---------------------------- GREATER THAN ---------------------------->
                            <!-- is type: other than Date -->
                            <b-form-input
                                v-if="validFilters[filter]?.type != Date"
                                :id="`${identifier}-advanced-filter-${filter}_gt`"
                                v-model="filters[`${filter}_gt`]"
                                v-b-tooltip.focus.v-danger="hasError(`${filter}_gt`)"
                                size="sm"
                                :state="hasError(`${filter}_gt`) ? false : null"
                                :placeholder="`${validFilters[filter]?.placeholder} greater`" />
                            <!-- is type: Date -->
                            <b-form-input
                                v-else-if="validFilters[filter]?.type == Date"
                                :id="`${identifier}-advanced-filter-${filter}_gt`"
                                v-model="dateFilters[`${filter}_gt`]"
                                v-b-tooltip.focus.v-danger="hasError(`${filter}_gt`)"
                                size="sm"
                                :state="hasError(`${filter}_gt`) ? false : null"
                                :placeholder="`${validFilters[filter]?.placeholder} after`" />
                            <b-input-group-append v-if="validFilters[filter]?.type == Date">
                                <b-form-datepicker
                                    v-model="dateFilters[`${filter}_gt`]"
                                    reset-button
                                    button-only
                                    size="sm" />
                            </b-input-group-append>
                            <!--------------------------------------------------------------------->

                            <!---------------------------- LESSER THAN ---------------------------->
                            <!-- is type: other than Date -->
                            <b-form-input
                                v-if="validFilters[filter]?.type != Date"
                                :id="`${identifier}-advanced-filter-${filter}_lt`"
                                v-model="filters[`${filter}_lt`]"
                                v-b-tooltip.focus.v-danger="hasError(`${filter}_lt`)"
                                size="sm"
                                :state="hasError(`${filter}_lt`) ? false : null"
                                :placeholder="`${validFilters[filter]?.placeholder} lower`" />
                            <!-- is type: Date -->
                            <b-form-input
                                v-else-if="validFilters[filter]?.type == Date"
                                :id="`${identifier}-advanced-filter-${filter}_lt`"
                                v-model="dateFilters[`${filter}_lt`]"
                                v-b-tooltip.focus.v-danger="hasError(`${filter}_lt`)"
                                size="sm"
                                :state="hasError(`${filter}_lt`) ? false : null"
                                :placeholder="`${validFilters[filter]?.placeholder} before`" />
                            <b-input-group-append v-if="validFilters[filter]?.type == Date">
                                <b-form-datepicker
                                    v-model="dateFilters[`${filter}_lt`]"
                                    reset-button
                                    button-only
                                    size="sm" />
                            </b-input-group-append>
                            <!--------------------------------------------------------------------->
                        </b-input-group>
                    </span>

                    <!-- is a MultiTags filter -->
                    <span v-else-if="validFilters[filter]?.type == 'MultiTags'">
                        <small>Filter by {{ validFilters[filter]?.placeholder }}:</small>
                        <b-input-group :id="`${identifier}-advanced-filter-${filter}`">
                            <StatelessTags
                                :value="multiTagFilters[filter]?.value"
                                :placeholder="`any ${validFilters[filter]?.placeholder}`"
                                @input="(tags) => onTags(filter, tags)" />
                        </b-input-group>
                    </span>

                    <!-- is any other non-Ranged/non-Boolean filter -->
                    <span v-else>
                        <small>Filter by {{ validFilters[filter]?.placeholder }}:</small>
                        <b-input-group>
                            <!-- has a datalist -->
                            <b-form-input
                                v-if="validFilters[filter]?.datalist"
                                :id="`${identifier}-advanced-filter-${filter}`"
                                v-model="filters[filter]"
                                v-b-tooltip.focus.v-danger="hasError(filter)"
                                size="sm"
                                :state="hasError(filter) ? false : null"
                                :placeholder="`any ${validFilters[filter]?.placeholder}`"
                                list="selectList" />
                            <b-form-datalist
                                v-if="validFilters[filter]?.datalist"
                                id="selectList"
                                :options="validFilters[filter]?.datalist"></b-form-datalist>
                            <!-- is type: Date -->
                            <b-form-input
                                v-else-if="validFilters[filter]?.type == Date"
                                :id="`${identifier}-advanced-filter-${filter}`"
                                v-model="dateFilters[filter]"
                                v-b-tooltip.focus.v-danger="hasError(filter)"
                                size="sm"
                                :state="hasError(filter) ? false : null"
                                :placeholder="`any ${validFilters[filter]?.placeholder}`" />
                            <!-- is type: other than Date -->
                            <b-form-input
                                v-else
                                :id="`${identifier}-advanced-filter-${filter}`"
                                v-model="filters[filter]"
                                v-b-tooltip.focus.v-danger="hasError(filter)"
                                size="sm"
                                :state="hasError(filter) ? false : null"
                                :placeholder="`any ${validFilters[filter]?.placeholder}`" />
                            <!-- append Help Modal for filter if included or/and datepciker if type: Date -->
                            <b-input-group-append>
                                <b-button
                                    v-if="validFilters[filter]?.helpInfo"
                                    :title="`${capitalize(validFilters[filter]?.placeholder)} Help`"
                                    size="sm"
                                    @click="helpModals[filter] = true">
                                    <icon icon="question" />
                                </b-button>
                                <b-form-datepicker
                                    v-if="validFilters[filter]?.type == Date"
                                    v-model="dateFilters[filter]"
                                    reset-button
                                    button-only
                                    size="sm" />
                            </b-input-group-append>
                        </b-input-group>
                    </span>

                    <!-- if a filter has help component, place it within a modal -->
                    <span v-if="validFilters[filter]?.helpInfo">
                        <b-modal
                            v-model="helpModals[filter]"
                            :title="`${capitalize(validFilters[filter]?.placeholder)} Help`"
                            ok-only>
                            <component
                                :is="validFilters[filter]?.helpInfo"
                                v-if="typeof validFilters[filter]?.helpInfo == 'object'"
                                @set-filter="onOption" />
                            <div v-else-if="typeof validFilters[filter]?.helpInfo == 'string'">
                                <p>{{ validFilters[filter]?.helpInfo }}</p>
                            </div>
                        </b-modal>
                    </span>
                </span>
            </div>

            <!-- Perform search or cancel out (or open help modal for Menu if exists) -->
            <div class="mt-3">
                <b-button
                    :id="`${identifier}-advanced-filter-submit`"
                    class="mr-1"
                    size="sm"
                    variant="primary"
                    data-description="apply filters"
                    @click="onSearch">
                    <icon icon="search" />
                    <span v-localize>Search</span>
                </b-button>
                <b-button v-if="props.menuType !== 'standalone'" size="sm" @click="onToggle">
                    <icon icon="redo" />
                    <span v-localize>Cancel</span>
                </b-button>
                <b-button v-if="props.hasHelp" title="Search Help" size="sm" @click="showHelp = true">
                    <icon icon="question" />
                </b-button>
                <span> </span>
                <b-modal v-if="props.hasHelp" v-model="showHelp" :title="`${props.name} Advanced Search Help`" ok-only>
                    <!-- Slot for Menu help section -->
                    <slot name="menu-help-text"></slot>
                </b-modal>
            </div>
        </div>
    </div>
</template>

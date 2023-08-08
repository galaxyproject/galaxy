<script setup lang="ts">
import { capitalize, kebabCase } from "lodash";
import { computed, type Ref, ref, watch } from "vue";

import type { Alias, ValidFilter } from "@/utils/filtering";
import type Filtering from "@/utils/filtering";
import { getOperatorForAlias } from "@/utils/filtering";

import FilterMenuRadio from "@/components/Common/FilterMenuRadio.vue";

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
        name?: string;
        placeholder?: string;
        filterClass: Filtering<any>;
        filterText: string;
        hasHelp?: boolean;
        searchError?: BackendFilterError;
        showAdvanced?: boolean;
    }>(),
    {
        name: "Menu",
        placeholder: "search for items",
        filterText: "",
        showAdvanced: false,
        searchError: undefined,
    }
);

const emit = defineEmits<{
    (e: "update:show-advanced", showAdvanced: boolean): void;
    (e: "update:filter-text", filter: string): void;
    (e: "show-help", filter: string, show: boolean): void;
}>();

const defaultBoolOptions = [
    { text: "Yes", value: true },
    { text: "No", value: false },
];

const localFilterText = computed({
    get: () => {
        return props.filterText;
    },
    set: (newVal: any) => {
        if (newVal !== props.filterText) {
            updateFilterText(newVal as string);
        }
    },
});

const validFilters = computed(() => props.filterClass.validFilters);

const filters = computed(() => Object.fromEntries(props.filterClass.getFiltersForText(localFilterText.value)));

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
 * (This was done to make the datepickers store values in the `filters` object)
 */
const dateFilters: Ref<{ [key: string]: string }> = ref({});
const dateKeys = Object.keys(validFilters.value).filter((key) => validFilters.value[key]?.type == Date);
dateKeys.forEach((key: string) => {
    if (validFilters.value[key]?.isRangeInput) {
        dateKeys.push(key + "_lt");
        dateKeys.push(key + "_gt");
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
    onToggle();
    Object.keys(dateFilters.value).forEach((key) => {
        onOption(key, dateFilters.value[key]);
    });
    updateFilterText(props.filterClass.getFilterText(filters.value));
}

function onToggle() {
    emit("update:show-advanced", !props.showAdvanced);
}

function updateFilterText(newFilterText: string) {
    emit("update:filter-text", newFilterText);
}
</script>

<template>
    <div>
        <b-input-group>
            <b-form-input
                :id="`${identifier}-filter`"
                v-model="localFilterText"
                size="sm"
                :class="filterText && 'font-weight-bold'"
                :placeholder="props.placeholder"
                data-description="filter text input"
                debounce="400"
                @keyup.esc="updateFilterText('')" />
            <b-input-group-append>
                <b-button
                    :id="`${identifier}-advanced-filter-toggle`"
                    v-b-tooltip.hover
                    aria-haspopup="true"
                    size="sm"
                    :pressed="showAdvanced"
                    :variant="showAdvanced ? 'info' : 'secondary'"
                    data-description="show advanced filter toggle"
                    title="Show Advanced Filter"
                    aria-label="Show advanced filter"
                    @click="onToggle">
                    <icon v-if="showAdvanced" icon="angle-double-up" />
                    <icon v-else icon="angle-double-down" />
                </b-button>
                <b-button
                    v-b-tooltip.hover
                    aria-haspopup="true"
                    size="sm"
                    title="Clear Filters (esc)"
                    aria-label="Clear filters"
                    data-description="clear filters"
                    @click="updateFilterText('')">
                    <icon icon="times" />
                </b-button>
            </b-input-group-append>
        </b-input-group>
        <!-- eslint-disable-next-line vuejs-accessibility/no-static-element-interactions -->
        <div
            v-if="showAdvanced"
            class="mt-2"
            data-description="advanced filters"
            @keyup.enter="onSearch"
            @keyup.esc="onToggle">
            <div v-for="filter in Object.keys(validFilters)" :key="filter">
                <span v-if="validFilters[filter]?.menuItem">
                    <!-- is a Radio filter -->
                    <span v-if="validFilters[filter]?.type == 'Radio'">
                        <small>{{ validFilters[filter]?.placeholder }}:</small>
                        <FilterMenuRadio
                            v-if="validFilters[filter]?.options"
                            :filter="filter"
                            :options="validFilters[filter]?.options"
                            :settings="filters"
                            @change="onOption" />
                    </span>

                    <!-- is a Boolean filter -->
                    <span v-else-if="validFilters[filter]?.type == Boolean">
                        <small>{{ validFilters[filter]?.placeholder }}:</small>
                        <b-form-group class="m-0">
                            <b-form-radio-group
                                v-model="filters[filter]"
                                :options="defaultBoolOptions"
                                size="sm"
                                buttons
                                :data-description="`filter ${filter}`" />
                        </b-form-group>
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
                <b-button size="sm" @click="onToggle">
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

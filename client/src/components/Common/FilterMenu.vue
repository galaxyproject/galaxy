<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faAngleDoubleUp, faQuestion, faSearch } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, BModal, BPopover } from "bootstrap-vue";
import { kebabCase } from "lodash";
import { computed, ref, set } from "vue";

import type Filtering from "@/utils/filtering";
import { type Alias, type ErrorType, getOperatorForAlias, type ValidFilter } from "@/utils/filtering";

import DelayedInput from "@/components/Common/DelayedInput.vue";
import FilterMenuBoolean from "@/components/Common/FilterMenuBoolean.vue";
import FilterMenuDropdown from "@/components/Common/FilterMenuDropdown.vue";
import FilterMenuInput from "@/components/Common/FilterMenuInput.vue";
import FilterMenuMultiTags from "@/components/Common/FilterMenuMultiTags.vue";
import FilterMenuObjectStore from "@/components/Common/FilterMenuObjectStore.vue";
import FilterMenuRanged from "@/components/Common/FilterMenuRanged.vue";

library.add(faAngleDoubleUp, faQuestion, faSearch);

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
    /** What view to use for the menu */
    view?: "dropdown" | "popover" | "compact";
}

const props = withDefaults(defineProps<Props>(), {
    name: "Menu",
    placeholder: "search for items",
    debounceDelay: 500,
    filterText: "",
    menuType: "linked",
    showAdvanced: false,
    searchError: undefined,
    view: "dropdown",
});

const emit = defineEmits<{
    (e: "update:filter-text", filter: string): void;
    (e: "update:show-advanced", showAdvanced: boolean): void;
    (e: "on-search", filters: Record<string, string | boolean>, filterText?: string, backendFilter?: string): void;
}>();

const validFilters = computed(() => props.filterClass.validFilters);

const filters = computed(() => Object.fromEntries(props.filterClass.getFiltersForText(props.filterText)));

const identifier = kebabCase(props.name);

const advancedMenu = ref<HTMLElement | null>(null);
const delayedInputField = ref<InstanceType<typeof DelayedInput> | null>(null);
const toggleMenuButton = computed(() => {
    const element = delayedInputField.value?.$el.querySelector(`[data-description='toggle advanced search']`);
    return element;
});

// Boolean for showing the help modal for the whole filter menu (if provided)
const showHelp = ref(false);

const isDisabled = ref<Record<string, boolean>>({});

const formattedSearchError = computed<ErrorType | null>(() => {
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

// computed ref with a get and set function
const localAdvancedToggle = computed({
    get: () => props.showAdvanced,
    set: (value: boolean) => {
        emit("update:show-advanced", value);
    },
});

/** Returns the `typeError` or `msg` for a given `field` */
function errorForField(field: string) {
    if (formattedSearchError.value && formattedSearchError.value?.index == field) {
        return formattedSearchError.value.typeError || formattedSearchError.value.msg;
    }
    return "";
}

/** Returns the `ValidFilter<any>` for given `filter`
 *
 * This non-null asserts the output because where it's used, the filter is guaranteed
 * to exist because of the `<span v-if="validFilters[filter]?.menuItem">` condition
 * @param filter the filter to get
 * @returns the _defined_ `ValidFilter<any>` for the given `filter`
 */
function getValidFilter(filter: string): ValidFilter<any> {
    return validFilters.value[filter]!;
}

/** Explicitly sets a filter: value
 * (also closes help modal for this filter if it exists)
 * @param filter the filter to set
 * @param value the value to set it to
 */
function onOption(filter: string, value: any) {
    filters.value[filter] = value;

    setDisabled(filter, value);

    // for the compact view, we want to immediately search
    if (props.view === "compact") {
        onSearch();
    }
}

function onPopoverShown() {
    advancedMenu.value?.querySelector("input")?.focus();
}

function onPopoverHidden() {
    (toggleMenuButton.value as any)?.focus();
}

function onSearch() {
    const newFilterText = props.filterClass.getFilterText(filters.value);
    const newBackendFilter = props.filterClass.getFilterText(filters.value, true);
    if (props.menuType !== "linked") {
        emit("on-search", filters.value, newFilterText, newBackendFilter);
    } else {
        updateFilterText(newFilterText);

        // for the compact view, we do not want to close the advanced menu
        if (props.view !== "compact") {
            onToggle();
        }
    }
}

function onToggle() {
    emit("update:show-advanced", !props.showAdvanced);
}

function setDisabled(filter: string, newVal: any) {
    const disablesFilters = validFilters.value[filter]?.disablesFilters;
    const type = validFilters.value[filter]?.type;
    if (disablesFilters && type !== Boolean) {
        for (const [disabledFilter, disablingValues] of Object.entries(disablesFilters)) {
            if (newVal && (disablingValues === null || disablingValues.includes(newVal))) {
                set(isDisabled.value, disabledFilter, true);
                filters.value[disabledFilter] = undefined;
            } else {
                set(isDisabled.value, disabledFilter, false);
            }
        }
    }
}

function updateFilterText(newFilterText: string) {
    emit("update:filter-text", newFilterText);
}
</script>

<template>
    <div>
        <DelayedInput
            v-if="props.menuType !== 'standalone'"
            v-show="props.menuType == 'linked' || (props.menuType == 'separate' && !props.showAdvanced)"
            ref="delayedInputField"
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

        <component
            :is="props.view !== 'popover' ? 'div' : BPopover"
            v-if="
                (props.view === 'popover' && toggleMenuButton) || props.menuType == 'standalone' || props.showAdvanced
            "
            class="mt-2"
            :show.sync="localAdvancedToggle"
            :target="toggleMenuButton"
            placement="bottomleft"
            data-description="advanced filters"
            @hidden="onPopoverHidden"
            @shown="onPopoverShown">
            <span ref="advancedMenu">
                <div v-for="filter in Object.keys(validFilters)" :key="filter">
                    <span v-if="validFilters[filter]?.menuItem">
                        <!-- Boolean filters go in another section in compact view -->
                        <FilterMenuBoolean
                            v-if="props.view !== 'compact' && validFilters[filter]?.type == Boolean"
                            :name="filter"
                            :filter="getValidFilter(filter)"
                            :filters="filters"
                            :view="props.view"
                            @change="onOption"
                            @on-enter="onSearch"
                            @on-esc="onToggle" />
                        <FilterMenuRanged
                            v-else-if="validFilters[filter]?.isRangeInput"
                            class="m-0"
                            :name="filter"
                            :filter="getValidFilter(filter)"
                            :filters="filters"
                            :error="formattedSearchError || undefined"
                            :identifier="identifier"
                            :disabled="isDisabled[filter] || false"
                            @change="onOption"
                            @on-enter="onSearch"
                            @on-esc="onToggle" />
                        <FilterMenuMultiTags
                            v-else-if="validFilters[filter]?.type == 'MultiTags'"
                            :name="filter"
                            :filter="getValidFilter(filter)"
                            :filters="filters"
                            :identifier="identifier"
                            @change="onOption" />
                        <FilterMenuObjectStore
                            v-else-if="validFilters[filter]?.type == 'ObjectStore'"
                            :name="filter"
                            :filter="getValidFilter(filter)"
                            :filters="filters"
                            @change="onOption" />
                        <FilterMenuDropdown
                            v-else-if="
                                validFilters[filter]?.type == 'Dropdown' || validFilters[filter]?.type == 'QuotaSource'
                            "
                            :type="validFilters[filter]?.type"
                            :name="filter"
                            :error="errorForField(filter) || undefined"
                            :filter="getValidFilter(filter)"
                            :filters="filters"
                            :identifier="identifier"
                            :disabled="isDisabled[filter] || false"
                            @change="onOption" />
                        <FilterMenuInput
                            v-else-if="validFilters[filter]?.type !== Boolean"
                            :name="filter"
                            :filter="getValidFilter(filter)"
                            :filters="filters"
                            :error="errorForField(filter) || undefined"
                            :identifier="identifier"
                            :disabled="isDisabled[filter] || false"
                            @change="onOption"
                            @on-enter="onSearch"
                            @on-esc="onToggle" />
                    </span>
                </div>
            </span>

            <!-- Compact view: Boolean filters go side by side -->
            <div v-if="props.view === 'compact'" class="d-flex">
                <span v-for="filter in Object.keys(validFilters)" :key="filter">
                    <FilterMenuBoolean
                        v-if="validFilters[filter]?.menuItem && validFilters[filter]?.type == Boolean"
                        class="mr-2 mt-1"
                        :name="filter"
                        :filter="getValidFilter(filter)"
                        :filters="filters"
                        :view="props.view"
                        @change="onOption"
                        @on-enter="onSearch"
                        @on-esc="onToggle" />
                </span>
            </div>

            <!-- Perform search or cancel out (or open help modal for whole Menu if exists) -->
            <div class="mt-2">
                <BButton
                    v-if="props.view !== 'compact'"
                    :id="`${identifier}-advanced-filter-submit`"
                    class="mr-1"
                    size="sm"
                    variant="primary"
                    data-description="apply filters"
                    @click="onSearch">
                    <FontAwesomeIcon :icon="faSearch" />

                    <span v-localize>Search</span>
                </BButton>

                <BButton v-if="props.hasHelp" title="Search Help" size="sm" @click="showHelp = true">
                    <FontAwesomeIcon :icon="faQuestion" />
                </BButton>

                <BModal v-if="props.hasHelp" v-model="showHelp" :title="`${props.name} Advanced Search Help`" ok-only>
                    <!-- Slot for Menu help section -->
                    <slot name="menu-help-text"></slot>
                </BModal>
            </div>
            <hr v-if="props.showAdvanced" class="w-100" />
        </component>
    </div>
</template>

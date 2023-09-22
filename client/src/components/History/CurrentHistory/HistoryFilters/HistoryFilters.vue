<template>
    <div>
        <b-input-group>
            <DebouncedInput v-slot="{ value, input }" v-model="localFilter">
                <b-form-input
                    size="sm"
                    :class="filterText && 'font-weight-bold'"
                    :value="value"
                    :placeholder="'search datasets' | localize"
                    data-description="filter text input"
                    @input="input"
                    @keyup.esc="updateFilter('')" />
            </DebouncedInput>
            <b-input-group-append>
                <b-button
                    v-b-tooltip.hover
                    aria-haspopup="true"
                    size="sm"
                    :pressed="showAdvanced"
                    :variant="showAdvanced ? 'info' : 'secondary'"
                    data-description="show advanced filter toggle"
                    title="Show Advanced Filter"
                    aria-label="Show advanced filter"
                    @click="onToggle">
                    <icon v-if="showAdvanced" fixed-width icon="angle-double-up" />
                    <icon v-else fixed-width icon="angle-double-down" />
                </b-button>
                <b-button
                    v-b-tooltip.hover
                    aria-haspopup="true"
                    size="sm"
                    title="Clear Filters (esc)"
                    aria-label="Clear filters"
                    data-description="clear filters"
                    @click="updateFilter('')">
                    <icon fixed-width icon="times" />
                </b-button>
            </b-input-group-append>
        </b-input-group>
        <div
            v-if="showAdvanced"
            class="mt-2"
            description="advanced filters"
            @keyup.enter="onSearch"
            @keyup.esc="onToggle">
            <small>Filter by name:</small>
            <b-form-input v-model="filterSettings['name:']" size="sm" placeholder="any name" />
            <small class="mt-1">Filter by extension:</small>
            <b-form-input v-model="filterSettings['extension:']" size="sm" placeholder="any extension" />
            <small class="mt-1">Filter by tag:</small>
            <b-form-input v-model="filterSettings['tag:']" size="sm" placeholder="any tag" />
            <small class="mt-1">Filter by state:</small>
            <b-input-group>
                <b-form-input
                    v-model="filterSettings['state:']"
                    v-b-tooltip.focus.v-danger="hasError('state:')"
                    :class="hasError('state:') && 'ui-input-error'"
                    size="sm"
                    placeholder="any state"
                    list="stateSelect" />
                <b-form-datalist id="stateSelect" :options="states"></b-form-datalist>
                <b-input-group-append>
                    <b-button title="States Help" size="sm" @click="showHelp = true">
                        <icon icon="question" />
                    </b-button>
                </b-input-group-append>
                <StatesInfo :show-help.sync="showHelp" :exclude-states="excludeStates" @set-filter="onOption" />
            </b-input-group>
            <small>Filter by database:</small>
            <b-form-input v-model="filterSettings['genome_build:']" size="sm" placeholder="any database" />
            <small class="mt-1">Filter by related to item index:</small>
            <b-form-input
                v-model="filterSettings['related:']"
                v-b-tooltip.focus.v-danger="hasError('related:')"
                :class="hasError('related:') && 'ui-input-error'"
                size="sm"
                placeholder="index equals" />
            <small class="mt-1">Filter by item index:</small>
            <b-form-group class="m-0">
                <b-input-group>
                    <b-form-input
                        v-model="filterSettings['hid>']"
                        v-b-tooltip.focus.v-danger="hasError('hid>')"
                        :class="hasError('hid>') && 'ui-input-error'"
                        size="sm"
                        placeholder="index greater" />
                    <b-form-input
                        v-model="filterSettings['hid<']"
                        v-b-tooltip.focus.v-danger="hasError('hid<')"
                        :class="hasError('hid<') && 'ui-input-error'"
                        size="sm"
                        placeholder="index lower" />
                </b-input-group>
            </b-form-group>
            <small class="mt-1">Filter by creation time:</small>
            <b-form-group class="m-0">
                <b-input-group>
                    <b-form-input
                        v-model="create_time_gt"
                        v-b-tooltip.focus.v-danger="hasError('create_time>')"
                        :class="hasError('create_time>') && 'ui-input-error'"
                        size="sm"
                        placeholder="created after" />
                    <b-input-group-append>
                        <b-form-datepicker v-model="create_time_gt" reset-button button-only size="sm" />
                    </b-input-group-append>
                    <b-form-input
                        v-model="create_time_lt"
                        v-b-tooltip.focus.v-danger="hasError('create_time<')"
                        :class="hasError('create_time<') && 'ui-input-error'"
                        size="sm"
                        placeholder="created before" />
                    <b-input-group-append>
                        <b-form-datepicker v-model="create_time_lt" reset-button button-only size="sm" />
                    </b-input-group-append>
                </b-input-group>
            </b-form-group>
            <history-filters-default :settings="filterSettings" @change="onOption" />
            <div class="mt-3">
                <b-button class="mr-1" size="sm" variant="primary" description="apply filters" @click="onSearch">
                    <icon icon="search" />
                    <span>{{ "Search" | localize }}</span>
                </b-button>
                <b-button size="sm" @click="onToggle">
                    <icon icon="redo" />
                    <span>{{ "Cancel" | localize }}</span>
                </b-button>
            </div>
        </div>
    </div>
</template>

<script>
import DebouncedInput from "components/DebouncedInput";
import HistoryFiltersDefault from "./HistoryFiltersDefault";
import { STATES } from "components/History/Content/model/states";
import StatesInfo from "components/History/Content/model/StatesInfo";
import { HistoryFilters } from "components/History/HistoryFilters";

export default {
    components: {
        DebouncedInput,
        HistoryFiltersDefault,
        StatesInfo,
    },
    props: {
        filterText: { type: String, default: null },
        showAdvanced: { type: Boolean, default: false },
        searchError: { type: Object, default: null },
    },
    data() {
        return {
            create_time_gt: "",
            create_time_lt: "",
            excludeStates: ["empty", "failed", "upload"],
            showHelp: false,
        };
    },
    computed: {
        filterSettings() {
            return HistoryFilters.toAlias(HistoryFilters.getFiltersForText(this.filterText));
        },
        localFilter: {
            get() {
                return this.filterText;
            },
            set(newVal) {
                if (newVal !== this.filterText) {
                    this.updateFilter(newVal);
                }
            },
        },
        states() {
            return Object.keys(STATES).filter((state) => !this.excludeStates.includes(state));
        },
    },
    watch: {
        filterSettings() {
            this.create_time_gt = this.filterSettings["create_time>"];
            this.create_time_lt = this.filterSettings["create_time<"];
        },
        showAdvanced(newVal) {
            this.showHelp = !newVal ? false : this.showHelp;
        },
    },
    methods: {
        hasError(field) {
            if (this.searchError && this.searchError.filter == field) {
                return this.searchError.typeError || this.searchError.msg;
            }
            return "";
        },
        onOption(name, value) {
            this.filterSettings[name] = value;
        },
        onSearch() {
            this.onToggle();
            this.filterSettings["create_time>"] = this.create_time_gt;
            this.filterSettings["create_time<"] = this.create_time_lt;
            // set values for deleted and visible => any, if removed previously
            if (this.filterSettings["deleted:"] === undefined) {
                this.filterSettings["deleted:"] = "any";
            }
            if (this.filterSettings["visible:"] === undefined) {
                this.filterSettings["visible:"] = "any";
            }
            this.updateFilter(HistoryFilters.getFilterText(this.filterSettings));
        },
        onToggle() {
            this.$emit("update:show-advanced", !this.showAdvanced);
        },
        updateFilter(newFilterText) {
            this.$emit("update:filter-text", newFilterText);
        },
    },
};
</script>

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
                    size="sm"
                    :pressed="showAdvanced"
                    :variant="showAdvanced ? 'info' : 'secondary'"
                    data-description="show advanced filter toggle"
                    @click="onToggle">
                    <icon v-if="showAdvanced" icon="angle-double-up" />
                    <icon v-else icon="angle-double-down" />
                </b-button>
                <b-button size="sm" data-description="show deleted filter toggle" @click="updateFilter('')">
                    <icon icon="times" />
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
            <b-form-input v-model="filterSettings['state:']" size="sm" placeholder="any state" list="stateSelect" />
            <b-form-datalist id="stateSelect" :options="states"></b-form-datalist>
            <small class="mt-1">Filter by item index:</small>
            <b-form-group class="m-0">
                <b-input-group>
                    <b-form-input v-model="filterSettings['hid>']" size="sm" placeholder="index greater" />
                    <b-form-input v-model="filterSettings['hid<']" size="sm" placeholder="index lower" />
                </b-input-group>
            </b-form-group>
            <small class="mt-1">Filter by creation time:</small>
            <b-form-group class="m-0">
                <b-input-group>
                    <b-form-input v-model="create_time_gt" size="sm" placeholder="created after" />
                    <b-input-group-append>
                        <b-form-datepicker v-model="create_time_gt" reset-button button-only size="sm" />
                    </b-input-group-append>
                    <b-form-input v-model="create_time_lt" size="sm" placeholder="created before" />
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
import { getFilters, toAlias } from "store/historyStore/model/filtering";
import DebouncedInput from "components/DebouncedInput";
import { STATES } from "components/History/Content/model/states";
import { getFilterText } from "./filterConversion";
import HistoryFiltersDefault from "./HistoryFiltersDefault";

export default {
    components: {
        DebouncedInput,
        HistoryFiltersDefault,
    },
    props: {
        filterText: { type: String, default: null },
        showAdvanced: { type: Boolean, default: false },
    },
    data() {
        return {
            create_time_gt: "",
            create_time_lt: "",
        };
    },
    computed: {
        filterSettings() {
            return toAlias(getFilters(this.filterText));
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
            return Object.keys(STATES);
        },
    },
    watch: {
        filterSettings() {
            this.create_time_gt = this.filterSettings["create_time>"];
            this.create_time_lt = this.filterSettings["create_time<"];
        },
    },
    methods: {
        onOption(name, value) {
            this.filterSettings[name] = value;
        },
        onSearch() {
            this.onToggle();
            this.filterSettings["create_time>"] = this.create_time_gt;
            this.filterSettings["create_time<"] = this.create_time_lt;
            this.updateFilter(getFilterText(this.filterSettings));
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

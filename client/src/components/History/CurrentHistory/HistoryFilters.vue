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
                    @keyup.esc="onReset" />
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
                <b-button size="sm" data-description="show deleted filter toggle" @click="onReset">
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
            <b-form-input v-model="filterSettings['name=']" size="sm" placeholder="any name" />
            <small class="mt-1">Filter by extension:</small>
            <b-form-input v-model="filterSettings['extension=']" size="sm" placeholder="any extension" />
            <small class="mt-1">Filter by tag:</small>
            <b-form-input v-model="filterSettings['tag=']" size="sm" placeholder="any tag" />
            <small class="mt-1">Filter by state:</small>
            <b-form-input v-model="filterSettings['state=']" size="sm" placeholder="any state" list="stateSelect" />
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
                    <b-form-input v-model="filterSettings['create_time>']" size="sm" placeholder="created after" />
                    <b-input-group-append>
                        <b-form-datepicker
                            v-model="filterSettings['create_time>']"
                            reset-button
                            button-only
                            size="sm" />
                    </b-input-group-append>
                    <b-form-input v-model="filterSettings['create_time<']" size="sm" placeholder="created before" />
                    <b-input-group-append>
                        <b-form-datepicker
                            v-model="filterSettings['create_time<']"
                            reset-button
                            button-only
                            size="sm" />
                    </b-input-group-append>
                </b-input-group>
            </b-form-group>
            <small>Show deleted:</small>
            <b-form-checkbox v-model="filterSettings['deleted=']" size="sm" switch description="filter deleted" />
            <small>Show visible:</small>
            <b-form-checkbox v-model="filterSettings['visible=']" size="sm" switch description="filter visible" />
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
import { getFilters, toAlias } from "store/historyStore/model/filtering";
import { STATES } from "../Content/model/states";

// available filter keys with operator and default setting
const filterDefaults = {
    "create_time>": "",
    "create_time<": "",
    "deleted=": false,
    "extension=": "",
    "hid>": "",
    "hid<": "",
    "name=": "",
    "state=": "",
    "tag=": "",
    "visible=": true,
};

export default {
    components: {
        DebouncedInput,
    },
    props: {
        filterText: { type: String, default: null },
        showAdvanced: { type: Boolean, default: false },
    },
    data() {
        return {
            filterSettings: { ...filterDefaults },
        };
    },
    computed: {
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
        localFilter(newFilterText) {
            // get dict in form of converted aliases
            const newFilterSettings = toAlias(getFilters(newFilterText));
            // reset filterSettings when filterText changes
            this.filterSettings = { ...filterDefaults };
            // update filterSettings
            Object.assign(this.filterSettings, newFilterSettings);
        },
    },
    methods: {
        onReset() {
            this.updateFilter("");
        },
        onSearch() {
            let newFilterText = "";
            Object.entries(this.filterSettings).filter(([key, value]) => {
                if (value !== filterDefaults[key]) {
                    if (newFilterText) {
                        newFilterText += " ";
                    }
                    if (String(value).includes(" ")) {
                        value = `'${value}'`;
                    }
                    newFilterText += `${key}${value}`;
                }
            });
            this.onToggle();
            this.updateFilter(newFilterText);
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

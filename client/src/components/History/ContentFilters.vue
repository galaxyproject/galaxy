<template>
    <b-input-group>
        <DebouncedInput v-model.trim="filterText" v-slot="{ value, input }">
            <b-form-input size="sm" :value="value" @input="input" :placeholder="'Search Filter' | localize" />
        </DebouncedInput>

        <b-button
            size="sm"
            :pressed="showDeleted"
            :variant="showDeleted ? 'info' : 'secondary'"
            @click="showDeleted = !showDeleted"
        >
            {{ "Deleted" | localize }}
        </b-button>
        <b-button
            size="sm"
            :pressed="showHidden"
            :variant="showHidden ? 'info' : 'secondary'"
            @click="showHidden = !showHidden"
        >
            {{ "Hidden" | localize }}
        </b-button>
    </b-input-group>
</template>

<script>
import { SearchParams } from "./model/SearchParams";
import DebouncedInput from "components/DebouncedInput";

export default {
    components: {
        DebouncedInput,
    },
    props: {
        filters: { type: SearchParams, required: true },
    },
    computed: {
        skip: {
            get() {
                return this.filters.skip;
            },
            set(newSkip) {
                const newParams = this.filters.clone();
                newParams.skip = newSkip;
                this.updateFilters(newParams);
            },
        },
        filterText: {
            get() {
                return this.filters.filterText;
            },
            set(newVal) {
                const newParams = this.filters.clone();
                newParams.filterText = newVal;
                this.updateFilters(newParams);
            },
        },
        showDeleted: {
            get() {
                return this.filters.showDeleted;
            },
            set(newFlag) {
                const newParams = this.filters.clone();
                newParams.showDeleted = newFlag;
                this.updateFilters(newParams);
            },
        },
        showHidden: {
            get() {
                return this.filters.showHidden;
            },
            set(newFlag) {
                const newParams = this.filters.clone();
                newParams.showHidden = newFlag;
                this.updateFilters(newParams);
            },
        },
    },
    methods: {
        updateFilters(newVal) {
            this.$emit("update:filters", newVal);
        },
    },
};
</script>

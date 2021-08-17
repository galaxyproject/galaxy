<template>
    <b-input-group v-if="params">
        <DebouncedInput v-model.trim="filterText" v-slot="{ value, input }">
            <b-form-input size="sm" :value="value" @input="input" :placeholder="'Search Filter' | localize" />
        </DebouncedInput>

        <b-input-group-append>
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
        </b-input-group-append>
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
        params: { type: SearchParams, required: true },
    },
    computed: {
        skip: {
            get() {
                return this.params.skip;
            },
            set(newSkip) {
                const newParams = this.params.clone();
                newParams.skip = newSkip;
                this.updateParams(newParams);
            },
        },
        filterText: {
            get() {
                return this.params.filterText;
            },
            set(newVal) {
                const newParams = this.params.clone();
                newParams.filterText = newVal;
                this.updateParams(newParams);
            },
        },
        showDeleted: {
            get() {
                return this.params.showDeleted;
            },
            set(newFlag) {
                const newParams = this.params.clone();
                newParams.showDeleted = newFlag;
                this.updateParams(newParams);
            },
        },
        showHidden: {
            get() {
                return this.params.showHidden;
            },
            set(newFlag) {
                const newParams = this.params.clone();
                newParams.showHidden = newFlag;
                this.updateParams(newParams);
            },
        },
    },
    methods: {
        updateParams(newParams) {
            this.$emit("update:params", newParams);
        },
    },
};
</script>

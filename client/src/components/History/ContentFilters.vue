<template>
    <b-input-group v-if="params">
        <DebouncedInput v-model.trim="filterText" v-slot="{ value, input }">
            <b-form-input
                size="sm"
                :value="value"
                @input="input"
                :placeholder="'Search Filter' | localize"
                data-description="filter text input" />
        </DebouncedInput>

        <b-input-group-append>
            <b-button
                size="sm"
                :pressed="showDeleted"
                :variant="showDeleted ? 'info' : 'secondary'"
                @click="showDeleted = !showDeleted"
                data-description="show deleted filter toggle">
                {{ "Deleted" | localize }}
            </b-button>
            <b-button
                size="sm"
                :pressed="showHidden"
                :variant="showHidden ? 'info' : 'secondary'"
                @click="showHidden = !showHidden"
                data-description="show hidden filter toggle">
                {{ "Hidden" | localize }}
            </b-button>
        </b-input-group-append>
    </b-input-group>
</template>

<script>
import { SearchParams } from "components/providers/History/SearchParams";
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

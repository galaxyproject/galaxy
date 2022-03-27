<template>
    <b-input-group v-if="params">
        <DebouncedInput v-model="filterText" v-slot="{ value, input }">
            <b-form-input
                size="sm"
                :value="value"
                @input="input"
                :placeholder="'search datasets' | localize"
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
import DebouncedInput from "components/DebouncedInput";

export default {
    components: {
        DebouncedInput,
    },
    props: {
        params: { type: Object, required: true },
    },
    computed: {
        filterText: {
            get() {
                return this.params.filterText;
            },
            set(newVal) {
                const newParams = Object.assign({}, this.params);
                newParams.filterText = newVal;
                this.updateParams(newParams);
            },
        },
        showDeleted: {
            get() {
                return this.params.showDeleted;
            },
            set(newFlag) {
                const newParams = Object.assign({}, this.params);
                newParams.showDeleted = newFlag;
                this.updateParams(newParams);
            },
        },
        showHidden: {
            get() {
                return this.params.showHidden;
            },
            set(newFlag) {
                const newParams = Object.assign({}, this.params);
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

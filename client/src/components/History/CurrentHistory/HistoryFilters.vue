<template>
    <div>
        <b-input-group class="mb-2">
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
                    <icon icon="trash" />
                </b-button>
                <b-button
                    size="sm"
                    :pressed="showAdvanced"
                    :variant="showAdvanced ? 'info' : 'secondary'"
                    @click="showAdvanced = !showAdvanced"
                    data-description="show advanced filter toggle">
                    <span>...</span>
                </b-button>
            </b-input-group-append>
        </b-input-group>
        <div v-if="!showAdvanced">
            <small>Filter by item index:</small>
            <b-form-group class="mb-1">
                <b-input-group>
                    <b-form-input size="sm" placeholder="index lower" />
                    <b-form-input size="sm" placeholder="index greater" />
                </b-input-group>
            </b-form-group>
            <small>Filter by creation date:</small>
            <b-form-group class="mb-1">
                <b-input-group>
                    <b-form-input size="sm" placeholder="created before" />
                    <b-form-input size="sm" placeholder="created after" />
                </b-input-group>
            </b-form-group>
            <b-form-group class="mb-1">
                <small>Filter by state:</small>
                <b-form-select value="select state" size="sm" :options="['select state', 'success', 'error']" />
            </b-form-group>
            <b-form-group>
                <small>Filter by extension:</small>
                <b-form-input size="sm" placeholder="extension" />
            </b-form-group>
            <b-button class="mr-1" size="sm" variant="primary">
                <icon icon="search" />
                <span>{{ "Search" | localize }}</span>
            </b-button>
            <b-button size="sm">
                <icon icon="redo" />
                <span>{{ "Cancel" | localize }}</span>
            </b-button>
        </div>
    </div>
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
    data() {
        return {
            showAdvanced: false,
        };
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

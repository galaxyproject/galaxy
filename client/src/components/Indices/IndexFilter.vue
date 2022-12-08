<template>
    <span>
        <b-input-group>
            <DebouncedInput v-slot="{ value: debouncedValue, input }" v-model="localFilter" :delay="debounceDelay">
                <b-form-input
                    :id="id"
                    name="query"
                    :value="debouncedValue"
                    autocomplete="off"
                    :placeholder="placeholder | localize"
                    data-description="filter index input"
                    class="search-query"
                    :size="size"
                    @input="input"
                    @keyup.esc="onReset" />
            </DebouncedInput>
            <b-input-group-append>
                <b-button
                    data-description="show deleted filter toggle"
                    title="Advanced Filtering Help"
                    :size="size"
                    @click="onHelp">
                    <icon icon="question" />
                </b-button>
            </b-input-group-append>
        </b-input-group>
        <b-modal v-model="showHelp" title="Filtering Options Help" ok-only>
            <div v-html="helpHtml"></div>
        </b-modal>
    </span>
</template>

<script>
import DebouncedInput from "components/DebouncedInput";

import { BInputGroup, BInputGroupAppend, BButton, BModal } from "bootstrap-vue";

/**
 * Component for the search/filter button on the top of Galaxy object index grids.
 */
export default {
    components: {
        DebouncedInput,
        BInputGroup,
        BInputGroupAppend,
        BButton,
        BModal,
    },
    props: {
        id: {
            type: String,
            required: true,
        },
        placeholder: {
            type: String,
            required: true,
        },
        helpHtml: {
            type: String,
            required: true,
        },
        debounceDelay: {
            type: Number,
            default: 500,
        },
        size: {
            type: String,
            default: "sm",
        },
        value: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            showHelp: false,
            localFilter: this.value,
        };
    },
    watch: {
        value(newValue) {
            this.localFilter = newValue;
        },
        localFilter(newVal) {
            this.$emit("input", newVal);
        },
    },
    methods: {
        onHelp() {
            this.showHelp = true;
        },
        onReset() {
            this.localFilter = "";
        },
    },
};
</script>

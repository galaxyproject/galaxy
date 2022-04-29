<template>
    <span>
        <b-input-group>
            <DebouncedInput :delay="debounceDelay" v-slot="{ value, input }" v-model="localFilter">
                <b-form-input
                    :id="id"
                    name="query"
                    :value="value"
                    autocomplete="off"
                    :placeholder="placeholder | localize"
                    data-description="filter index input"
                    @input="input"
                    @keyup.esc="onReset" />
            </DebouncedInput>
            <b-input-group-append>
                <b-button data-description="show deleted filter toggle" @click="onHelp" title="Advanced Filtering Help">
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
        value: {},
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

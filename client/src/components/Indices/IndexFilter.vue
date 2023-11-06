<template>
    <span>
        <BInputGroup>
            <DebouncedInput v-slot="{ value: debouncedValue, input }" v-model="localFilter" :delay="debounceDelay">
                <b-form-input
                    :id="id"
                    name="query"
                    :value="debouncedValue"
                    autocomplete="off"
                    :placeholder="placeholder | localize"
                    data-description="filter index input"
                    class="search-query index-filter-query"
                    :size="size"
                    @input="input"
                    @keyup.esc="onReset" />
            </DebouncedInput>
            <BInputGroupAppend>
                <BButton
                    v-b-tooltip.hover
                    aria-haspopup="true"
                    title="Advanced Filtering Help"
                    :size="size"
                    @click="onHelp">
                    <FontAwesomeIcon icon="question" />
                </BButton>
                <BButton
                    v-b-tooltip.hover
                    aria-haspopup="true"
                    title="Clear Filters (esc)"
                    :size="size"
                    @click="onReset">
                    <FontAwesomeIcon icon="times" />
                </BButton>
            </BInputGroupAppend>
        </BInputGroup>
        <BModal v-model="showHelp" title="Filtering Options Help" ok-only>
            <div v-html="helpHtml"></div>
        </BModal>
    </span>
</template>

<script>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faQuestion, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, BInputGroup, BInputGroupAppend, BModal } from "bootstrap-vue";
import DebouncedInput from "components/DebouncedInput";

library.add(faTimes, faQuestion);

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
        FontAwesomeIcon,
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

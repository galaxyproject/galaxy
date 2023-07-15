<template>
    <span>
        <GInputGroup>
            <DebouncedInput v-slot="{ value: debouncedValue, input }" v-model="localFilter" :delay="debounceDelay">
                <GInput
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
            <GInputGroupAppend>
                <GButton
                    v-b-tooltip.hover
                    aria-haspopup="true"
                    title="Advanced Filtering Help"
                    :size="size"
                    @click="onHelp">
                    <FontAwesomeIcon icon="question" />
                </GButton>
                <GButton
                    v-b-tooltip.hover
                    aria-haspopup="true"
                    title="Clear Filters (esc)"
                    :size="size"
                    @click="onReset">
                    <FontAwesomeIcon icon="times" />
                </GButton>
            </GInputGroupAppend>
        </GInputGroup>
        <BModal v-model="showHelp" title="Filtering Options Help" ok-only>
            <div v-html="helpHtml"></div>
        </BModal>
    </span>
</template>

<script>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faQuestion, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BModal } from "bootstrap-vue";
import DebouncedInput from "components/DebouncedInput";

import GButton from "component-library/GButton.vue";
import GInput from "component-library/GInput.vue";
import GInputGroup from "component-library/GInputGroup.vue";
import GInputGroupAppend from "component-library/GInputGroupAppend.vue";

library.add(faTimes, faQuestion);

/**
 * Component for the search/filter button on the top of Galaxy object index grids.
 */
export default {
    components: {
        DebouncedInput,
        GButton,
        GInputGroup,
        GInputGroupAppend,
        BModal,
        FontAwesomeIcon,
        GInput,
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

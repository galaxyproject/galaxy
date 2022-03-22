<template>
    <click-to-edit
        class="annotation"
        tag-name="p"
        :value="annotation"
        ref="annotationInput"
        v-b-tooltip.hover="{ boundary: 'viewport', placement: tooltipPlacement }"
        :title="'Edit annotation...' | localize"
        :placeholder="'Edit annotation...' | localize"
        v-slot="{ toggleEdit, placeholder, stateValidator }">
        <debounced-input v-model="annotation" :delay="1000" v-slot="inputScope">
            <b-form-textarea
                size="sm"
                tabindex="-1"
                rows="3"
                no-resize
                :value="inputScope.value"
                @input="inputScope.input"
                @blur="toggleEdit(false)"
                :placeholder="placeholder"
                :state="stateValidator(inputScope.value, annotation)"></b-form-textarea>
        </debounced-input>
    </click-to-edit>
</template>

<script>
import DebouncedInput from "./DebouncedInput";
import ClickToEdit from "./ClickToEdit";

export default {
    components: {
        DebouncedInput,
        ClickToEdit,
    },
    props: {
        value: { type: String, required: false, default: "" },
        tooltipPlacement: { type: String, required: false, default: "left" },
    },
    computed: {
        annotation: {
            get() {
                return this.value || "";
            },
            set(newVal, oldVal) {
                if (newVal !== oldVal) {
                    this.$emit("input", newVal);
                }
            },
        },
    },
};
</script>

<style lang="scss" scoped>
.annotation >>> p {
    position: relative;
    font-style: italic;
    display: -webkit-box;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 3;
    overflow: hidden;
    text-overflow: ellipsis;
}
</style>

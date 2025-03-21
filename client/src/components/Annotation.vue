<template>
    <ClickToEdit
        ref="annotationInput"
        v-slot="{ toggleEdit, placeholder, stateValidator }"
        v-b-tooltip.hover="{ boundary: 'viewport', placement: tooltipPlacement }"
        class="annotation"
        tag-name="p"
        :value="annotation"
        :title="'编辑注释...' | localize"
        :placeholder="'编辑注释...' | localize">
        <DebouncedInput v-slot="inputScope" v-model="annotation" :delay="1000">
            <b-form-textarea
                size="sm"
                tabindex="-1"
                rows="3"
                no-resize
                :value="inputScope.value"
                :placeholder="placeholder"
                :state="stateValidator(inputScope.value, annotation)"
                @input="inputScope.input"
                @blur="toggleEdit(false)"></b-form-textarea>
        </DebouncedInput>
    </ClickToEdit>
</template>

<script>
import ClickToEdit from "./ClickToEdit";
import DebouncedInput from "./DebouncedInput";

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

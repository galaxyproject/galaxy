<template>
    <div class="clickToEdit" :class="{ empty: !value.length }">
        <component :is="tagName" v-if="!editing" class="m-0" @click="toggleEdit(true)">
            <span class="editable"></span>
            <span>{{ displayValue }}</span>
            <slot name="tooltip" :editing="editing" :local-value="localValue"></slot>
        </component>

        <component :is="tagName" v-if="editing">
            <slot
                :toggle-edit="toggleEdit"
                :editing="editing"
                :placeholder="placeholder"
                :state-validator="stateValidator">
                <debounced-input v-model="localValue" :delay="debounceDelay">
                    <template v-slot="{ value: debouncedValue, input }">
                        <b-form-input
                            ref="clickToEditInput"
                            :value="debouncedValue"
                            :placeholder="placeholder"
                            :state="stateValidator(debouncedValue, localValue)"
                            @input="input"
                            @blur="toggleEdit(false)" />
                    </template>
                </debounced-input>
            </slot>
        </component>
    </div>
</template>

<script>
import DebouncedInput from "./DebouncedInput";

const defaultStateValidator = (val, origVal) => {
    if (val === origVal) {
        return null;
    }
    return val.length > 0;
};

export default {
    components: {
        DebouncedInput,
    },
    props: {
        value: { type: String, required: true },
        tagName: { type: String, required: false, default: "h2" },
        placeholder: { type: String, required: false, default: "" },
        stateValidator: { type: Function, required: false, default: defaultStateValidator },
        debounceDelay: { type: Number, required: false, default: 1000 },
    },
    data() {
        return {
            editing: false,
        };
    },
    computed: {
        displayValue() {
            return this.localValue || this.placeholder;
        },
        localValue: {
            get() {
                return this.value;
            },
            set(newVal, oldVal) {
                if (newVal !== oldVal) {
                    this.$emit("input", newVal);
                    // closes click to edit if it didn't close on its own
                    this.$refs["clickToEditInput"].blur();
                }
            },
        },
    },
    methods: {
        toggleEdit(forceVal) {
            this.editing = forceVal !== undefined ? forceVal : !this.editing;
        },
    },
};
</script>

<style lang="scss" scoped>
@import "theme/blue.scss";
@import "~scss/mixins.scss";

.clickToEdit {
    position: relative;
    &:hover .editable {
        @include fontawesome($fa-var-edit);
        position: absolute;
        top: 0;
        right: 0;
        color: $brand-info;
        font-size: 0.8rem;
    }
    /* changes placeholder text, it's a brittle and ugly selector
    but bootstrap-vue doesn't give us much to work with */
    &.empty > p > span {
        color: adjust-color($text-color, $alpha: -0.6);
        font-style: italic;
    }
}

h1 input {
    font-size: $h1-font-size;
    font-weight: 500;
}

h2 input {
    font-size: $h2-font-size;
    font-weight: 500;
}

h3 input {
    font-size: $h3-font-size;
    font-weight: 500;
}

h4 input {
    font-size: $h4-font-size;
    font-weight: 500;
}
</style>

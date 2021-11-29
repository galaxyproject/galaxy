<template>
    <b-button
        class="galaxy-icon-button"
        v-bind="$attrs"
        v-on="$listeners"
        :title="title"
        :size="size"
        :pressed="pressed"
        :disabled="disabled"
        :variant="localVariant">
        <Icon :icon="icon" />
        <span class="sr-only">{{ title | l }}</span>
    </b-button>
</template>

<script>
export default {
    props: {
        icon: { type: [String, Array, Object], required: true },
        title: { type: String, required: true },
        size: { type: String, required: false, default: "sm" },
        pressed: { type: Boolean, required: false, default: false },
        disabled: { type: Boolean, required: false, default: false },
        // overrides variant set by pressed/disabled
        variant: { type: String, required: false, default: null },
    },
    computed: {
        localVariant() {
            if (this.variant) {
                // override with prop
                return this.variant;
            }
            if (this.disabled) {
                return "secondary";
            }
            return this.pressed ? "info" : "secondary";
        },
    },
};
</script>

<style lang="scss">
// removes irritating bootstrap outline
.galaxy-icon-button.btn {
    box-shadow: none !important;
    &.disabled > svg {
        opacity: 0.5;
    }
}
</style>

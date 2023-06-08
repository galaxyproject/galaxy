<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";

const props = defineProps<{
    h1?: boolean;
    h2?: boolean;
    h3?: boolean;
    h4?: boolean;
    h5?: boolean;
    h6?: boolean;
    bold?: boolean;
    separator?: boolean;
    inline?: boolean;
    size?: "xl" | "lg" | "md" | "sm" | "text";
    icon?: string | [string, string];
}>();

const sizeClass = computed(() => {
    return `h-${props.size ?? "lg"}`;
});

const element = computed(() => {
    for (const key of ["h1", "h2", "h3", "h4", "h5", "h6"]) {
        if (props[key as keyof typeof props]) {
            return key;
        }
    }
    return "h1";
});
</script>

<template>
    <div v-if="props.separator" class="separator heading">
        <div class="stripe"></div>
        <component :is="element" :class="[sizeClass, props.bold ? 'font-weight-bold' : '']">
            <slot />
        </component>
        <div class="stripe"></div>
    </div>
    <component
        :is="element"
        v-else
        class="heading"
        :class="[sizeClass, props.bold ? 'font-weight-bold' : '', props.inline ? 'inline' : '']">
        <FontAwesomeIcon v-if="props.icon" :icon="props.icon" />
        <slot />
    </component>
</template>

<style lang="scss" scoped>
@import "scss/theme/blue.scss";

.heading:deep(svg) {
    font-size: 0.75em;
}

// prettier-ignore
h1, h2, h3, h4, h5, h6 {
    display: flex;
    align-items: center;
    gap: 0.4em;

    &.inline {
        display: inline-flex;
        margin-bottom: 0;
    }
}

.separator {
    display: grid;
    grid-template-columns: 1rem auto 1fr;
    gap: 1rem;
    align-items: center;
    margin-bottom: 0.5rem;

    // prettier-ignore
    h1, h2, h3, h4, h5, h6 {
        margin: 0;
    }

    .stripe {
        display: block;
        height: 1px;
        background-color: $brand-secondary;
    }
}
</style>

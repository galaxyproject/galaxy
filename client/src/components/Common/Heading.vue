<script setup>
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

let element = "h1";
let sizeClass = "h-lg";

const props = defineProps({
    h1: Boolean,
    h2: Boolean,
    h3: Boolean,
    h4: Boolean,
    h5: Boolean,
    h6: Boolean,
    bold: Boolean,
    separator: Boolean,
    inline: Boolean,
    // acceptable sizes are "xl", "lg", "md", "sm", and "text"
    size: String,
    icon: String,
});

// apply heading element
for (const key of ["h1", "h2", "h3", "h4", "h5", "h6"]) {
    if (props[key]) {
        element = key;
        break;
    }
}

// apply size class
if (props.size) {
    sizeClass = "h-" + props.size;
}
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

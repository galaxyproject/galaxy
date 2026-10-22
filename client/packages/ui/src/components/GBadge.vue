<script setup lang="ts">
/**
 * Small inline label for a count, status or tag. Renders a span by default, a router-link
 * for `to`, an anchor for `href`, or a button for `button`.
 */

import { computed } from "vue";
import { RouterLink } from "vue-router";

import type { BadgeVariant, ColorVariant } from "./componentVariants";

defineOptions({
    // Under @vue/compat: let listeners such as @click fall through to the root element, as in Vue 3
    compatConfig: { INSTANCE_LISTENERS: false },
});

const props = defineProps<{
    /** Color scheme; `outline-*` draws the color as border and text on the page background. Defaults to secondary */
    variant?: BadgeVariant;
    /** Fully rounded ends */
    pill?: boolean;
    /** Router link "to" prop. Renders the badge as a router-link */
    to?: string;
    /** Href for an anchor. Renders the badge as an anchor */
    href?: string;
    /** Renders the badge as a `type="button"` button, for badges that act on click */
    button?: boolean;
}>();

const baseComponent = computed(() => {
    if (props.button) {
        return "button" as const;
    } else if (props.to) {
        return RouterLink;
    } else if (props.href) {
        return "a" as const;
    } else {
        return "span" as const;
    }
});

// Only a plain anchor takes our href and only a RouterLink our `to`: a RouterLink builds its
// own href, including the router base, and any `href` key passed down replaces it.
const elementAttributes = computed(() => {
    if (baseComponent.value === "button") {
        return { type: "button" };
    } else if (baseComponent.value === "a") {
        return { href: props.href };
    } else if (baseComponent.value === RouterLink) {
        return { to: props.to };
    }
    return {};
});

const variantClasses = computed(() => {
    const variant = props.variant ?? "secondary";
    const outline = variant.startsWith("outline-");
    const color = (outline ? variant.slice("outline-".length) : variant) as ColorVariant;
    return {
        [`g-${color}`]: true,
        "g-outline": outline,
        "g-pill": props.pill,
    };
});
</script>

<template>
    <component :is="baseComponent" class="g-badge" :class="variantClasses" v-bind="elementAttributes">
        <slot></slot>
    </component>
</template>

<style scoped lang="scss">
.g-badge {
    display: inline-block;
    margin: 0;
    padding: 0.25em 0.4em;
    // Transparent on solid badges, so forced-colors mode still draws an edge.
    border: 1px solid transparent;
    border-radius: var(--spacing-1);
    font-family: inherit;
    font-size: var(--font-size-small);
    font-weight: bold;
    line-height: 1;
    text-align: center;
    text-decoration: none;
    white-space: nowrap;
    vertical-align: baseline;

    &.g-pill {
        padding-right: 0.6em;
        padding-left: 0.6em;
        border-radius: 10rem;
    }
}

a.g-badge,
button.g-badge {
    cursor: pointer;

    &:hover {
        text-decoration: underline;
    }

    &:focus {
        outline: none;
    }

    &:focus-visible {
        outline: 2px solid var(--color-blue-600);
        outline-offset: 2px;
        box-shadow: 0 0 0 2px var(--background-color);
    }
}

// Every text/background pair below has a contrast ratio of at least 4.5:1.
.g-badge {
    &.g-primary {
        background-color: var(--color-blue-600);
        color: var(--color-blue-100);
    }

    &.g-secondary {
        background-color: var(--color-grey-200);
        color: var(--color-grey-800);
    }

    &.g-success {
        background-color: var(--color-green-700);
        color: var(--color-green-100);
    }

    &.g-danger {
        background-color: var(--color-red-700);
        color: var(--color-red-100);
    }

    &.g-warning {
        background-color: var(--color-orange-600);
        color: var(--color-grey-900);
    }

    &.g-info {
        background-color: var(--color-blue-200);
        border-color: var(--color-blue-300);
        color: var(--color-blue-600);
    }

    &.g-light {
        background-color: var(--color-grey-100);
        border-color: var(--color-grey-200);
        color: var(--color-grey-800);
    }

    &.g-dark {
        background-color: var(--color-blue-700);
        color: var(--color-grey-100);
    }

    &.g-outline {
        background-color: var(--background-color);

        &.g-primary {
            border-color: var(--color-blue-600);
            color: var(--color-blue-600);
        }

        &.g-secondary {
            border-color: var(--color-grey-400);
            color: var(--color-grey-600);
        }

        &.g-success {
            border-color: var(--color-green-600);
            color: var(--color-green-700);
        }

        &.g-danger {
            border-color: var(--color-red-600);
            color: var(--color-red-700);
        }

        &.g-warning {
            border-color: var(--color-orange-600);
            color: var(--color-orange-700);
        }

        // A light fill keeps outline-info apart from outline-primary, which shares its text color.
        &.g-info {
            background-color: var(--color-blue-100);
            border-color: var(--color-blue-400);
            color: var(--color-blue-600);
        }

        &.g-light {
            border-color: var(--color-grey-300);
            color: var(--color-grey-500);
        }

        &.g-dark {
            border-color: var(--color-blue-700);
            color: var(--color-blue-700);
        }
    }
}
</style>

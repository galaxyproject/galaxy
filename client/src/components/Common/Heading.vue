<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faAngleDoubleDown, faAngleDoubleUp } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";

library.add(faAngleDoubleDown, faAngleDoubleUp);

interface Props {
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
    truncate?: boolean;
    collapse?: "open" | "closed" | "none";
}

const props = withDefaults(defineProps<Props>(), {
    collapse: "none",
    icon: "",
    size: "lg",
});

defineEmits(["click"]);

const sizeClass = computed(() => {
    return `h-${props.size}`;
});

const collapsible = computed(() => {
    return props.collapse !== "none";
});

const collapsed = computed(() => {
    return props.collapse === "closed";
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
        <b-button v-if="collapsible" variant="link" size="sm" @click="$emit('click')">
            <FontAwesomeIcon v-if="collapsed" fixed-width :icon="faAngleDoubleDown" />
            <FontAwesomeIcon v-else fixed-width :icon="faAngleDoubleUp" />
        </b-button>
        <div v-else class="stripe"></div>
        <component
            :is="element"
            :class="[
                sizeClass,
                props.bold ? 'font-weight-bold' : '',
                collapsible ? 'collapsible' : '',
                props.truncate ? 'truncate' : '',
            ]"
            @click="$emit('click')">
            <slot />
        </component>
        <div class="stripe"></div>
    </div>
    <component
        :is="element"
        v-else
        class="heading"
        :class="[
            sizeClass,
            props.bold ? 'font-weight-bold' : '',
            props.inline ? 'inline' : '',
            collapsible ? 'collapsible' : '',
            props.truncate ? 'truncate' : '',
        ]"
        @click="$emit('click')">
        <b-button v-if="collapsible" variant="link" size="sm">
            <icon v-if="collapsed" fixed-width icon="angle-double-down" />
            <icon v-else fixed-width icon="angle-double-up" />
        </b-button>
        <FontAwesomeIcon v-if="props.icon" :icon="props.icon" />
        <slot />
    </component>
</template>

<style lang="scss" scoped>
@import "scss/theme/blue.scss";

.heading {
    word-break: break-all;
}

.heading:deep(svg) {
    font-size: 0.75em;
}

// prettier-ignore
h1, h2, h3, h4, h5, h6 {
    &:not(.truncate) {
        display: flex;
    }
    align-items: center;
    gap: 0.4em;

    &.inline {
        display: inline-flex;
        margin-bottom: 0;
    }

    &.truncate {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
}

.collapsible {
    cursor: pointer;
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

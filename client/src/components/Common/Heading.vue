<script setup lang="ts">
import { faAngleDoubleDown, faAngleDoubleUp } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, nextTick, onMounted, onUpdated, ref } from "vue";

import type { IconLike } from "@/components/icons/galaxyIcons";

import GButton from "@/components/BaseComponents/GButton.vue";

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
    // TODO: Redo in Vue 3 to use BootstrapSize for prop typing.
    size?: "xs" | "sm" | "md" | "lg" | "xl" | "text";
    icon?: IconLike;
    truncate?: boolean;
    clamp?: number;
    collapse?: "open" | "closed" | "none";
}

const props = withDefaults(defineProps<Props>(), {
    collapse: "none",
    icon: undefined,
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

const headingRef = ref<HTMLElement | null>(null);
const isClamped = ref(false);

function checkClamped() {
    if (headingRef.value && props.clamp) {
        isClamped.value = headingRef.value.scrollHeight > headingRef.value.clientHeight;
    } else {
        isClamped.value = false;
    }
}

const clampTooltip = computed(() => {
    if (isClamped.value) {
        return headingRef.value?.textContent?.trim() ?? "";
    }
    return "";
});

const clampStyle = computed(() => {
    if (props.clamp) {
        return { webkitLineClamp: props.clamp };
    }
    return undefined;
});

onMounted(checkClamped);
onUpdated(() => nextTick(checkClamped));
</script>

<template>
    <div v-if="props.separator" class="separator heading word-wrap-break">
        <GButton v-if="collapsible" transparent size="small" icon-only inline @click="$emit('click')">
            <FontAwesomeIcon v-if="collapsed" fixed-width :icon="faAngleDoubleDown" />
            <FontAwesomeIcon v-else fixed-width :icon="faAngleDoubleUp" />
        </GButton>
        <div v-else class="stripe"></div>
        <component
            :is="element"
            ref="headingRef"
            v-b-tooltip.hover="clampTooltip"
            :class="[
                sizeClass,
                props.bold ? 'font-weight-bold' : '',
                collapsible ? 'collapsible' : '',
                props.truncate ? 'truncate' : '',
                props.clamp ? 'clamp' : '',
            ]"
            :style="clampStyle"
            @click="$emit('click')">
            <slot />
        </component>
        <div class="stripe"></div>
    </div>
    <component
        :is="element"
        v-else
        ref="headingRef"
        v-b-tooltip.hover="clampTooltip"
        class="heading word-wrap-break"
        :class="[
            sizeClass,
            props.bold ? 'font-weight-bold' : '',
            props.inline ? 'inline' : '',
            collapsible ? 'collapsible' : '',
            props.truncate ? 'truncate' : '',
            props.clamp ? 'clamp' : '',
        ]"
        :style="clampStyle"
        @click="$emit('click')">
        <GButton v-if="collapsible" transparent size="small" icon-only inline>
            <FontAwesomeIcon v-if="collapsed" fixed-width :icon="faAngleDoubleDown" />
            <FontAwesomeIcon v-else fixed-width :icon="faAngleDoubleUp" />
        </GButton>
        <FontAwesomeIcon v-if="props.icon" :icon="props.icon" />
        <slot />
    </component>
</template>

<style lang="scss" scoped>
@import "@/style/scss/theme/blue.scss";

// prettier-ignore
h1, h2, h3, h4, h5, h6 {
    &:not(.truncate):not(.clamp) {
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

    &.clamp {
        display: -webkit-box;
        -webkit-box-orient: vertical;
        overflow: hidden;
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

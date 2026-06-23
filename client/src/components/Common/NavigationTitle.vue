<script setup lang="ts">
import { faAngleDoubleDown, faAngleDoubleUp, type IconDefinition } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

import GButton from "@/components/BaseComponents/GButton.vue";

interface Props {
    /** Icon shown before the title text. */
    icon: IconDefinition;
    /** Plain title text. Use the `title` slot instead when richer content is needed. */
    title?: string;
    /** Optional `data-description` for the heading wrapper (test hook). */
    headingDescription?: string;
    /** Show a collapse/expand toggle and make the `collapsible` slot collapsible. */
    collapsible?: boolean;
    /** Current collapsed state — owned by the parent so it can persist and react to it. */
    collapsed?: boolean;
}

defineProps<Props>();

const emit = defineEmits<{
    (e: "toggle"): void;
}>();
</script>

<template>
    <div>
        <div class="bg-secondary px-2 py-1 rounded d-flex flex-gapx-1 justify-content-between">
            <div class="py-1 d-flex flex-wrap align-items-center flex-gapx-1" :data-description="headingDescription">
                <GButton
                    v-if="collapsible"
                    transparent
                    size="small"
                    icon-only
                    inline
                    :title="collapsed ? 'Expand header' : 'Collapse header'"
                    @click="emit('toggle')">
                    <FontAwesomeIcon :icon="collapsed ? faAngleDoubleDown : faAngleDoubleUp" fixed-width />
                </GButton>
                <slot name="before-icon" />
                <FontAwesomeIcon :icon="icon" fixed-width />
                <slot name="title">
                    <b>{{ title }}</b>
                </slot>
            </div>
            <div class="d-flex flex-gapx-1 align-self-baseline">
                <slot name="actions" />
            </div>
        </div>
        <Transition v-if="collapsible" name="navigation-title-collapse">
            <div v-if="!collapsed">
                <slot name="collapsible" />
            </div>
        </Transition>
    </div>
</template>

<style scoped lang="scss">
.navigation-title-collapse-enter-active,
.navigation-title-collapse-leave-active {
    overflow: hidden;
    max-height: 600px;
    opacity: 1;
    transform: translateY(0);
    transition:
        max-height 0.3s ease,
        opacity 0.25s ease,
        transform 0.25s ease;
}

.navigation-title-collapse-enter,
.navigation-title-collapse-enter-from,
.navigation-title-collapse-leave-to {
    max-height: 0;
    opacity: 0;
    transform: translateY(-6px);
}
</style>

<script setup lang="ts">
/**
 * Styled component for displaying an icon alongside a title and optional collapsible content,
 * with the icon and title placed on one line and the content placed in the same column as
 * the title. (A two-row, two-column layout with the icon and title in the first row and the
 * content in the second row.)
 *
 * The content is optionally collapsible.
 */

import type { IconDefinition } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { ref } from "vue";

import GCollapse from "@/components/BaseComponents/GCollapse.vue";
import Heading from "@/components/Common/Heading.vue";

const props = defineProps<{
    /** The icon to display in the detail block header */
    headerIcon: IconDefinition;
    /** The title to display in the detail block header */
    title: string;
    /** If `true`, the content is collapsible */
    collapsible?: boolean;
}>();

const collapseState = ref<"open" | "closed" | "none">(props.collapsible ? "open" : "none");

function toggleCollapse() {
    if (props.collapsible) {
        collapseState.value = collapseState.value === "open" ? "closed" : "open";
    }
}
</script>

<template>
    <div>
        <div class="detail-block">
            <div class="detail-block-icon">
                <FontAwesomeIcon :icon="props.headerIcon" />
            </div>
            <Heading inline size="sm" bold separator :collapse="collapseState" @click="toggleCollapse">
                {{ props.title }}
            </Heading>

            <div class="detail-block-spacer" />
            <GCollapse :visible="collapseState !== 'closed'">
                <slot />
            </GCollapse>
        </div>
    </div>
</template>

<style scoped lang="scss">
// 2x2 grid: icon | heading (row 1), empty spacer | content (row 2)
.detail-block {
    display: grid;
    grid-template-columns: auto 1fr;
    align-items: center;
    row-gap: 0.5rem;
    column-gap: 0.5rem;

    .detail-block-icon {
        width: 30px;
        height: 30px;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
        background: var(--color-blue-100);
        border: 1px solid var(--color-grey-200);
        border-radius: 8px;
        color: var(--color-blue-600);
    }

    .detail-block-spacer {
        align-self: stretch;
    }

    .heading {
        margin-bottom: 0;
    }

    // TODO: Maybe we need to max-width all poppers to 70vw globally?
    :deep(.popper-element) {
        max-width: 70vw;
        text-align: left;
        white-space: normal !important;
    }
}
</style>

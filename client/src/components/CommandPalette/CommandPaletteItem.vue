<script setup lang="ts">
import { faExternalLinkAlt } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";

import { localize } from "@/utils/localization";

import type { PaletteItem } from "./types";

interface Props {
    /** Whether this option is the keyboard-selected one */
    active: boolean;
    /** DOM id, referenced by the input's aria-activedescendant */
    id: string;
    /** The palette item to render */
    item: PaletteItem;
    /** Previews that ctrl/cmd + enter would open this item in a new tab */
    showExternal?: boolean;
}

const props = withDefaults(defineProps<Props>(), { showExternal: false });

const emit = defineEmits<{
    (e: "select", event: MouseEvent): void;
    (e: "highlight"): void;
}>();

// providers keep their strings in English, the rows are localized where they render
const title = computed(() => localize(props.item.title));

const subtitle = computed(() => (props.item.subtitle ? localize(props.item.subtitle) : undefined));

/**
 * The key badge is decorative markup, so a row carrying one names itself and its
 * shortcut explicitly instead of leaving the key out of the accessible name.
 */
const ariaLabel = computed(() => (props.item.shortcut ? `${title.value} (${props.item.shortcut})` : undefined));
</script>

<template>
    <!-- Keyboard interaction is handled by the palette's combobox input -->
    <!-- eslint-disable-next-line vuejs-accessibility/click-events-have-key-events, vuejs-accessibility/interactive-supports-focus -->
    <div
        :id="props.id"
        class="command-palette-item"
        :class="{ active: props.active }"
        role="option"
        :aria-label="ariaLabel"
        :aria-selected="props.active ? 'true' : 'false'"
        data-description="palette option"
        @click="emit('select', $event)"
        @mousemove="emit('highlight')">
        <span class="item-icon" aria-hidden="true">
            <FontAwesomeIcon v-if="props.item.icon" fixed-width :icon="props.item.icon" />
        </span>

        <span class="item-text">
            <span class="item-title">{{ title }}</span>

            <span v-if="subtitle" class="item-subtitle">{{ subtitle }}</span>
        </span>

        <FontAwesomeIcon
            v-if="props.showExternal"
            class="item-external"
            data-description="palette option external"
            fixed-width
            :icon="faExternalLinkAlt" />

        <kbd v-else-if="props.item.shortcut" class="item-shortcut" aria-hidden="true">{{ props.item.shortcut }}</kbd>

        <kbd v-else-if="props.active" class="item-enter" aria-hidden="true">↵</kbd>
    </div>
</template>

<style scoped lang="scss">
.command-palette-item {
    display: flex;
    align-items: center;
    gap: var(--spacing-2);
    padding: var(--spacing-1) var(--spacing-3);
    position: relative;
    cursor: pointer;

    .item-icon {
        flex: none;
        color: var(--color-grey-500);
    }

    .item-text {
        display: flex;
        flex-direction: column;
        min-width: 0;

        .item-title {
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .item-subtitle {
            font-size: var(--font-size-small);
            color: var(--color-grey-600);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
    }

    .item-enter {
        margin-left: auto;
        font-size: var(--font-size-small);
        color: var(--color-grey-600);
        background: none;
    }

    .item-external {
        margin-left: auto;
        color: var(--color-blue-600);
    }

    .item-shortcut {
        margin-left: auto;
        padding: 0 var(--spacing-1);
        border: 1px solid var(--color-grey-300);
        border-radius: var(--spacing);
        background-color: var(--color-grey-100);
        color: var(--color-grey-600);
        font-size: var(--font-size-small);
    }

    &.active {
        background-color: var(--color-blue-100);

        .item-title {
            color: var(--color-blue-800);
            font-weight: 600;
        }
    }
}
</style>

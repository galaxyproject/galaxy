<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

import type { PaletteItem } from "./types";

interface Props {
    /** Whether this option is the keyboard-selected one */
    active: boolean;
    /** DOM id, referenced by the input's aria-activedescendant */
    id: string;
    /** The palette item to render */
    item: PaletteItem;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "select", event: MouseEvent): void;
    (e: "hover"): void;
}>();
</script>

<template>
    <!-- Keyboard interaction is handled by the palette's combobox input -->
    <!-- eslint-disable-next-line vuejs-accessibility/click-events-have-key-events, vuejs-accessibility/interactive-supports-focus -->
    <div
        :id="props.id"
        class="command-palette-item"
        :class="{ active: props.active }"
        role="option"
        :aria-selected="props.active ? 'true' : 'false'"
        data-description="palette option"
        @click="emit('select', $event)"
        @mousemove="emit('hover')">
        <span class="item-icon" aria-hidden="true">
            <FontAwesomeIcon v-if="props.item.icon" fixed-width :icon="props.item.icon" />
        </span>

        <span class="item-text">
            <span class="item-title">{{ props.item.title }}</span>

            <span v-if="props.item.subtitle" class="item-subtitle">{{ props.item.subtitle }}</span>
        </span>

        <kbd v-if="props.active" class="item-enter" aria-hidden="true">↵</kbd>
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
        color: var(--color-ebony-clay-500, var(--color-grey-500));
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
            color: var(--color-chicago-500, var(--color-grey-600));
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
    }

    .item-enter {
        margin-left: auto;
        font-size: var(--font-size-small);
        color: var(--color-ebony-clay-600, var(--color-grey-600));
        background: none;
    }

    &.active {
        background-color: var(--color-bay-of-many-100, var(--color-blue-100));

        &::before {
            content: "";
            position: absolute;
            left: 0;
            top: 0;
            bottom: 0;
            width: 3px;
            background-color: var(--color-gold-500, #ffd700);
        }

        .item-title {
            color: var(--color-bay-of-many-900, var(--color-blue-800));
            font-weight: 600;
        }
    }
}
</style>

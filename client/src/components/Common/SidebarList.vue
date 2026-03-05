<script setup lang="ts" generic="T">
import { faSpinner } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

const props = withDefaults(
    defineProps<{
        items: T[];
        isLoading: boolean;
        loadingMessage?: string;
        emptyMessage?: string;
        itemKey: (item: T) => string | number;
        itemClass?: (item: T, index: number) => string | Record<string, boolean> | undefined;
    }>(),
    {
        loadingMessage: "Loading...",
        emptyMessage: "No items found.",
        itemClass: undefined,
    },
);

const emit = defineEmits<{
    (e: "select", item: T, index: number, event: MouseEvent): void;
}>();

function onItemClick(item: T, index: number, event: MouseEvent) {
    emit("select", item, index, event);
}

function onItemKeydown(item: T, index: number, event: KeyboardEvent) {
    if (event.key === "Enter") {
        emit("select", item, index, event as unknown as MouseEvent);
    }
}
</script>

<template>
    <div class="sidebar-list" data-description="sidebar list">
        <div v-if="isLoading" class="text-center p-3" data-description="sidebar list loading">
            <FontAwesomeIcon :icon="faSpinner" spin />
            {{ loadingMessage }}
        </div>
        <div v-else-if="items.length === 0" class="text-muted p-3 text-center" data-description="sidebar list empty">
            {{ emptyMessage }}
        </div>
        <div v-else class="sidebar-items">
            <div
                v-for="(item, index) in items"
                :key="itemKey(item)"
                class="sidebar-item d-flex align-items-start p-2 border-bottom"
                :class="props.itemClass?.(item, index)"
                data-description="sidebar item"
                role="button"
                tabindex="0"
                @click="onItemClick(item, index, $event)"
                @keydown="onItemKeydown(item, index, $event)">
                <slot name="item" :item="item" :index="index" />
            </div>
        </div>
    </div>
</template>

<style scoped>
.sidebar-list {
    max-height: 100%;
    overflow-y: auto;
}
.sidebar-item:hover {
    background: var(--gray-200);
    cursor: pointer;
}
</style>

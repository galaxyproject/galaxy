<script setup lang="ts">
import { faSpinner } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

const props = withDefaults(
    defineProps<{
        items: any[];
        isLoading: boolean;
        loadingMessage?: string;
        emptyMessage?: string;
        itemKey: (item: any) => string | number;
        itemClass?: (item: any, index: number) => string | Record<string, boolean> | undefined;
        itemDataDescription?: string;
    }>(),
    {
        loadingMessage: "Loading...",
        emptyMessage: "No items found.",
        itemClass: undefined,
        itemDataDescription: "sidebar item",
    },
);

const emit = defineEmits<{
    (e: "select", item: any, index: number, event: MouseEvent): void;
}>();

function onItemClick(item: any, index: number, event: MouseEvent) {
    emit("select", item, index, event);
}

function onItemKeydown(item: any, index: number, event: KeyboardEvent) {
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
                :data-description="props.itemDataDescription"
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

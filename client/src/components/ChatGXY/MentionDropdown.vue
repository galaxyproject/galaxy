<script setup lang="ts">
import { autoUpdate, computePosition, flip, offset, shift } from "@floating-ui/dom";
import { faDatabase, faHistory } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { onBeforeUnmount, ref, watch } from "vue";

import type { HistoryItemSummary } from "@/api";
import { isHDA } from "@/api";
import type { EntityType } from "@/composables/useEntityMentions";
import { useHistoryItemsStore } from "@/stores/historyItemsStore";
import { useHistoryStore } from "@/stores/historyStore";

const props = defineProps<{
    visible: boolean;
    /** null = picking entity type, "dataset" or "history" = showing entity list */
    mentionType: EntityType | null;
    searchText: string;
    anchorEl: HTMLElement | null;
}>();

const emit = defineEmits<{
    (e: "select", entityType: EntityType, identifier: string, displayText: string): void;
    (e: "close"): void;
}>();

const dropdownEl = ref<HTMLElement | null>(null);
const selectedIndex = ref(0);

let cleanupAutoUpdate: (() => void) | null = null;

interface MenuItem {
    key: string;
    icon: typeof faDatabase;
    label: string;
    entityType: EntityType;
    identifier: string;
    displayText: string;
}

function getEntityTypeItems(): MenuItem[] {
    const items: MenuItem[] = [
        {
            key: "dataset",
            icon: faDatabase,
            label: "Dataset",
            entityType: "dataset",
            identifier: "",
            displayText: "",
        },
        {
            key: "history",
            icon: faHistory,
            label: "History",
            entityType: "history",
            identifier: "",
            displayText: "",
        },
    ];

    if (!props.searchText) {
        return items;
    }

    return items.filter((item) => item.label.toLowerCase().startsWith(props.searchText.toLowerCase()));
}

function getDatasetItems(): MenuItem[] {
    const historyStore = useHistoryStore();
    const historyItemsStore = useHistoryItemsStore();
    const historyId = historyStore.currentHistoryId;
    if (!historyId) {
        return [];
    }

    const allItems: HistoryItemSummary[] = historyItemsStore.getHistoryItems(historyId, "");
    const datasets = allItems.filter(isHDA);

    let filtered = datasets;
    if (props.searchText) {
        const search = props.searchText.toLowerCase();
        filtered = datasets.filter(
            (d) => (d.name ?? "").toLowerCase().includes(search) || String(d.hid).includes(search),
        );
    }

    return filtered.slice(0, 20).map((d) => ({
        key: `dataset-${d.hid}`,
        icon: faDatabase,
        label: `${d.hid}: ${d.name ?? "Untitled"} (${d.extension ?? "?"})`,
        entityType: "dataset" as EntityType,
        identifier: String(d.hid),
        displayText: `@dataset:${d.hid}`,
    }));
}

function getHistoryItems(): MenuItem[] {
    const historyStore = useHistoryStore();

    const items: MenuItem[] = [];

    // Always offer "current"
    const current = historyStore.currentHistory;
    if (current) {
        items.push({
            key: "history-current",
            icon: faHistory,
            label: `Current: ${current.name}`,
            entityType: "history",
            identifier: "current",
            displayText: "@history:current",
        });
    }

    if (props.searchText && props.searchText !== "current") {
        const search = props.searchText.toLowerCase();
        return items.filter((item) => item.label.toLowerCase().includes(search));
    }

    return items;
}

function getMenuItems(): MenuItem[] {
    if (props.mentionType === null) {
        return getEntityTypeItems();
    }
    if (props.mentionType === "dataset") {
        return getDatasetItems();
    }
    if (props.mentionType === "history") {
        return getHistoryItems();
    }
    return [];
}

function handleSelect(item: MenuItem) {
    if (props.mentionType === null) {
        // Selected entity type — emit with empty identifier to signal type selection
        emit("select", item.entityType, "", `@${item.entityType}:`);
    } else {
        emit("select", item.entityType, item.identifier, item.displayText);
    }
}

function handleKeydown(event: KeyboardEvent) {
    if (!props.visible) {
        return;
    }

    const items = getMenuItems();
    if (items.length === 0) {
        return;
    }

    if (event.key === "ArrowDown") {
        event.preventDefault();
        selectedIndex.value = (selectedIndex.value + 1) % items.length;
    } else if (event.key === "ArrowUp") {
        event.preventDefault();
        selectedIndex.value = (selectedIndex.value - 1 + items.length) % items.length;
    } else if (event.key === "Enter" || event.key === "Tab") {
        event.preventDefault();
        event.stopPropagation();
        const item = items[selectedIndex.value];
        if (item) {
            handleSelect(item);
        }
    } else if (event.key === "Escape") {
        event.preventDefault();
        emit("close");
    }
}

function updatePosition() {
    if (!props.anchorEl || !dropdownEl.value) {
        return;
    }

    computePosition(props.anchorEl, dropdownEl.value, {
        placement: "top-start",
        middleware: [offset(4), flip(), shift({ padding: 8 })],
    }).then(({ x, y }) => {
        if (dropdownEl.value) {
            Object.assign(dropdownEl.value.style, {
                left: `${x}px`,
                top: `${y}px`,
            });
        }
    });
}

watch(
    () => [props.visible, props.mentionType, props.searchText],
    () => {
        selectedIndex.value = 0;
        if (props.visible) {
            updatePosition();
        }
    },
);

watch(
    () => props.visible,
    (visible) => {
        if (visible && props.anchorEl && dropdownEl.value) {
            cleanupAutoUpdate = autoUpdate(props.anchorEl, dropdownEl.value, updatePosition);
        } else if (cleanupAutoUpdate) {
            cleanupAutoUpdate();
            cleanupAutoUpdate = null;
        }
    },
);

onBeforeUnmount(() => {
    if (cleanupAutoUpdate) {
        cleanupAutoUpdate();
    }
});

defineExpose({ handleKeydown });
</script>

<template>
    <div v-show="visible" ref="dropdownEl" class="mention-dropdown" role="listbox">
        <div v-if="getMenuItems().length === 0" class="mention-empty">No matches</div>
        <div
            v-for="(item, index) in getMenuItems()"
            :key="item.key"
            class="mention-item"
            role="option"
            tabindex="-1"
            :aria-selected="index === selectedIndex"
            :class="{ selected: index === selectedIndex }"
            @mouseenter="selectedIndex = index"
            @mousedown.prevent="handleSelect(item)">
            <FontAwesomeIcon :icon="item.icon" fixed-width class="mention-icon" />
            <span class="mention-label">{{ item.label }}</span>
        </div>
    </div>
</template>

<style lang="scss" scoped>
@import "@/style/scss/theme/blue.scss";

.mention-dropdown {
    position: fixed;
    z-index: 1050;
    background: $white;
    border: $border-default;
    border-radius: $border-radius-base;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
    min-width: 200px;
    max-width: 360px;
    max-height: 240px;
    overflow-y: auto;
    padding: 0.25rem 0;
}

.mention-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.4rem 0.75rem;
    cursor: pointer;
    font-size: 0.85rem;
    color: $text-color;

    &:hover,
    &.selected {
        background: rgba($brand-primary, 0.08);
    }
}

.mention-icon {
    color: $text-light;
    font-size: 0.75rem;
    flex-shrink: 0;
}

.mention-label {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.mention-empty {
    padding: 0.5rem 0.75rem;
    font-size: 0.8rem;
    color: $text-light;
    text-align: center;
}
</style>

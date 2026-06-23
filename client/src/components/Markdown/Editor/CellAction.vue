<template>
    <div>
        <CellButton ref="buttonRef" title="Actions" :show="show" :icon="faEllipsisV" />
        <Popper
            v-if="buttonRef"
            ref="popperRef"
            :reference-el="buttonRef.$el"
            trigger="click"
            placement="right"
            mode="light">
            <nav
                role="menu"
                aria-label="cell actions"
                tabindex="0"
                @click="popperRef.visible = false"
                @keydown.enter="popperRef.visible = false"
                @keydown.space.prevent="popperRef.visible = false">
                <span class="d-flex justify-content-between">
                    <small class="my-1 mx-3 text-info">{{ title }}</small>
                </span>
                <CellOption
                    role="menuitem"
                    title="Clone"
                    description="Create a copy of this cell"
                    :icon="faClone"
                    @click="$emit('clone')" />
                <CellOption
                    role="menuitem"
                    title="Delete"
                    description="Delete this cell"
                    :icon="faTrash"
                    @click="onDeleteCell" />
                <CellOption
                    v-if="cellIndex > 0"
                    role="menuitem"
                    title="Move Up"
                    description="Move this cell upwards"
                    :icon="faArrowUp"
                    @click="$emit('move', 'up')" />
                <CellOption
                    v-if="cellTotal - cellIndex > 1"
                    role="menuitem"
                    title="Move Down"
                    description="Move this cell downwards"
                    :icon="faArrowDown"
                    @click="$emit('move', 'down')" />
            </nav>
        </Popper>
    </div>
</template>

<script setup lang="ts">
import { faClone, faEllipsisV } from "@fortawesome/free-solid-svg-icons";
import { faArrowDown, faArrowUp, faTrash } from "font-awesome-6";
import { computed, ref } from "vue";

import { useConfirmDialog } from "@/composables/confirmDialog";

import type { CellType } from "./types";

import CellButton from "./CellButton.vue";
import CellOption from "./CellOption.vue";
import Popper from "@/components/Popper/Popper.vue";

const props = withDefaults(
    defineProps<{
        cellIndex: number;
        cellTotal: number;
        configurable?: boolean;
        name: string;
        show?: boolean;
    }>(),
    {
        configurable: false,
        show: true,
    },
);

const emit = defineEmits<{
    (e: "click", cell: CellType): void;
    (e: "clone"): void;
    (e: "configure"): void;
    (e: "delete"): void;
    (e: "move", direction: string): void;
}>();

const { confirm } = useConfirmDialog();

const buttonRef = ref();
const popperRef = ref();

const title = computed(() => `${props.name.charAt(0).toUpperCase()}${props.name.slice(1)}`);

async function onDeleteCell() {
    const confirmed = await confirm("Are you sure you want to delete this cell?", "Delete Cell");
    if (confirmed) {
        emit("delete");
    }
}
</script>

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
            <div @click="popperRef.visible = false">
                <span class="d-flex justify-content-between">
                    <small class="my-1 mx-3 text-info">{{ title }}</small>
                </span>
                <CellOption
                    v-if="cellIndex > 0"
                    title="Move Up"
                    description="Move this cell upwards"
                    :icon="faArrowUp"
                    @click="$emit('move', 'up')" />
                <CellOption
                    v-if="cellTotal - cellIndex > 1"
                    title="Move Down"
                    description="Move this cell downwards"
                    :icon="faArrowDown"
                    @click="$emit('move', 'down')" />
                <CellOption
                    v-if="name !== 'markdown'"
                    title="Attach Data"
                    description="Select data for this cell"
                    :icon="faPaperclip"
                    @click="$emit('configure')" />
                <CellOption
                    title="Clone"
                    description="Create a copy of this cell"
                    :icon="faClone"
                    @click="$emit('clone')" />
                <CellOption
                    title="Delete"
                    description="Delete this cell"
                    :icon="faTrash"
                    @click="confirmDelete = true" />
            </div>
        </Popper>
        <BModal v-model="confirmDelete" title="Delete Cell" title-tag="h2" @ok="$emit('delete')">
            <p v-localize>Are you sure you want to delete this cell?</p>
        </BModal>
    </div>
</template>

<script setup lang="ts">
import { faClone, faEllipsisV } from "@fortawesome/free-solid-svg-icons";
import { BModal } from "bootstrap-vue";
import { faArrowDown, faArrowUp, faPaperclip, faTrash } from "font-awesome-6";
import { computed, ref } from "vue";

import type { CellType } from "./types";

import CellButton from "./CellButton.vue";
import CellOption from "./CellOption.vue";
import Popper from "@/components/Popper/Popper.vue";

const props = defineProps<{
    cellIndex: number;
    cellTotal: number;
    name: string;
    show: boolean;
}>();

defineEmits<{
    (e: "click", cell: CellType): void;
    (e: "clone"): void;
    (e: "configure"): void;
    (e: "delete"): void;
    (e: "move", direction: string): void;
}>();

const buttonRef = ref();
const confirmDelete = ref(false);
const popperRef = ref();

const title = computed(() => `${props.name.charAt(0).toUpperCase()}${props.name.slice(1)}`);
</script>

<style>
.cell-add-categories {
    max-height: 20rem;
    max-width: 15rem;
    min-width: 15rem;
}
</style>

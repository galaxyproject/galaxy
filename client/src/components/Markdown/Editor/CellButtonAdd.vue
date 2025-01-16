<template>
    <Popper trigger="click" placement="right" mode="light">
        <template v-slot:reference>
            <span
                v-b-tooltip.right
                role="button"
                tabindex="0"
                class="d-inline text-muted ml-3 cursor-pointer"
                title="Insert new Cell">
                <FontAwesomeIcon class="text-primary" :icon="faPlusSquare" />
            </span>
        </template>
        <div class="cursor-pointer">
            <CellOption
                title="Markdown"
                description="Markdown text element"
                :icon="faPlusSquare"
                @click="onClick('markdown')" />
            <CellOption
                title="Galaxy Element"
                description="Galaxy element"
                :icon="faPlusSquare"
                @click="onClick('galaxy')" />
            <CellOption title="Vega" description="Vega Graphics" :icon="faPlusSquare" @click="onClick('vega')" />
            <CellOption
                title="Vitessce"
                description="Vitessce Graphics"
                :icon="faPlusSquare"
                @click="onClick('vitessce')" />
        </div>
    </Popper>
</template>

<script setup lang="ts">
import { faPlusSquare } from "@fortawesome/free-regular-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

import CellOption from "./CellOption.vue";
import Popper from "@/components/Popper/Popper.vue";

const props = defineProps<{
    cellIndex: number;
}>();

const emit = defineEmits<{
    (e: "click", cellIndex: number, cellType: string): void;
}>();

function onClick(cellType: string) {
    emit("click", props.cellIndex, cellType);
}
</script>

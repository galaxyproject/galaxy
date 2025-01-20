<template>
    <Popper trigger="click" placement="right" mode="light">
        <template v-slot:reference>
            <b-button
                v-b-tooltip.right
                class="border-0 m-1 py-0 px-1"
                title="Insert new Cell"
                variant="outline-primary">
                <FontAwesomeIcon :icon="faPlusSquare" />
            </b-button>
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

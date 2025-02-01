<template>
    <div class="cell-guide d-flex flex-column justify-content-between">
        <CellButton ref="buttonRef" title="Insert new Cell">
            <FontAwesomeIcon :icon="faPlus" />
        </CellButton>
        <Popper v-if="buttonRef" :reference-el="buttonRef.$el" trigger="click" placement="right" mode="light">
            <div class="cursor-pointer">
                <CellOption
                    title="Markdown"
                    description="Markdown text element"
                    :icon="faPlus"
                    @click="onClick('markdown')" />
                <CellOption
                    title="Galaxy Element"
                    description="Galaxy element"
                    :icon="faPlus"
                    @click="onClick('galaxy')" />
                <CellOption title="Vega" description="Vega Graphics" :icon="faPlus" @click="onClick('vega')" />
                <CellOption
                    title="Vitessce"
                    description="Vitessce Graphics"
                    :icon="faPlus"
                    @click="onClick('vitessce')" />
            </div>
        </Popper>
    </div>
</template>

<script setup lang="ts">
import { faPlus } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { ref } from "vue";

import CellButton from "./CellButton.vue";
import CellOption from "./CellOption.vue";
import Popper from "@/components/Popper/Popper.vue";

const props = defineProps<{
    cellIndex: number;
}>();

const emit = defineEmits<{
    (e: "click", cellIndex: number, cellType: string): void;
}>();

const buttonRef = ref();

function onClick(cellType: string) {
    emit("click", props.cellIndex, cellType);
}
</script>

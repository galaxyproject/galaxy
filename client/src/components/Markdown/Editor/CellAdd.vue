<template>
    <Popper trigger="click" placement="right" mode="light">
        <template v-slot:reference>
            <div class="cell-guide d-flex flex-column justify-content-between">
                <CellButton title="Insert new Cell">
                    <FontAwesomeIcon :icon="faPlus" />
                </CellButton>
            </div>
        </template>
        <div class="cursor-pointer">
            <CellOption
                title="Markdown"
                description="Markdown text element"
                :icon="faPlus"
                @click="onClick('markdown')" />
            <CellOption title="Galaxy Element" description="Galaxy element" :icon="faPlus" @click="onClick('galaxy')" />
            <CellOption title="Vega" description="Vega Graphics" :icon="faPlus" @click="onClick('vega')" />
            <CellOption title="Vitessce" description="Vitessce Graphics" :icon="faPlus" @click="onClick('vitessce')" />
        </div>
    </Popper>
</template>

<script setup lang="ts">
import { faPlus } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

import CellButton from "./CellButton.vue";
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

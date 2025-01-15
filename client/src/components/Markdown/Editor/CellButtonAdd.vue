<template>
    <Popper trigger="click" placement="right" mode="light" :arrow="false">
        <template v-slot:reference>
            <div v-b-tooltip.right class="d-inline text-muted ml-2 cursor-pointer" title="Insert new Cell">
                <FontAwesomeIcon :icon="faPlusSquare" />
            </div>
        </template>
        <div class="cursor-pointer">
            <CellOption
                title="Markdown"
                description="Markdown text element"
                :icon="faPlusSquare"
                @click="onClick('markdown')" />
            <CellOption title="Vega" description="Vega Graphics" @click="onClick('vega')" />
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

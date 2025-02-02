<template>
    <div class="cell-guide d-flex flex-column justify-content-between">
        <CellButton ref="buttonRef" title="Insert Cell">
            <FontAwesomeIcon :icon="faPlus" />
        </CellButton>
        <Popper v-if="buttonRef" :reference-el="buttonRef.$el" trigger="click" placement="right" mode="light">
            <div class="cursor-pointer">
                <CellOption
                    v-for="(option, optionIndex) of options"
                    :key="optionIndex"
                    :title="option.title"
                    :description="option.description"
                    @click="$emit('click', { ...option.cell, toggle: true })" />
            </div>
        </Popper>
    </div>
</template>

<script setup lang="ts">
import { faPlus } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { ref } from "vue";

import type { CellType } from "./types";

import CellButton from "./CellButton.vue";
import CellOption from "./CellOption.vue";
import Popper from "@/components/Popper/Popper.vue";

defineEmits<{
    (e: "click", cell: CellType): void;
}>();

const buttonRef = ref();
const options = ref([
    {
        title: "Markdown",
        description: "Vitessce Graphics",
        cell: {
            name: "markdown",
            content: "",
        },
    },
    {
        title: "Vega",
        description: "Vitessce Graphics",
        cell: {
            name: "vega",
            content: "",
        },
    },
    {
        title: "Vitessce",
        description: "Vitessce Graphics",
        cell: {
            name: "markdown",
            content: "",
        },
    },
]);
</script>

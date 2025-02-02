<template>
    <div class="cell-guide d-flex flex-column justify-content-between">
        <CellButton ref="buttonRef" title="Insert Cell">
            <FontAwesomeIcon :icon="faPlus" />
        </CellButton>
        <Popper v-if="buttonRef" :reference-el="buttonRef.$el" trigger="click" placement="right" mode="light">
            <DelayedInput class="p-1" :delay="100" placeholder="Search" @change="query = $event" />
            <div class="cursor-pointer overflow-auto" style="max-height: 20rem">
                <div v-for="(category, categoryIndex) of getTemplates(query)" :key="categoryIndex">
                    <hr class="solid m-0" />
                    <span class="d-flex justify-content-between">
                        <small class="my-1 mx-3 text-info">{{ category.name }}</small>
                    </span>
                    <div v-if="category.templates.length > 0">
                        <CellOption
                            v-for="(option, optionIndex) of category.templates"
                            :key="optionIndex"
                            :title="option.title"
                            :description="option.description"
                            @click="$emit('click', { ...option.cell, toggle: true })" />
                    </div>
                </div>
            </div>
        </Popper>
    </div>
</template>

<script setup lang="ts">
import { faPlus } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { ref } from "vue";

import { getTemplates } from "./templates";
import type { CellType } from "./types";

import CellButton from "./CellButton.vue";
import CellOption from "./CellOption.vue";
import DelayedInput from "@/components/Common/DelayedInput.vue";
import Popper from "@/components/Popper/Popper.vue";

defineEmits<{
    (e: "click", cell: CellType): void;
}>();

const buttonRef = ref();
const query = ref("");
</script>

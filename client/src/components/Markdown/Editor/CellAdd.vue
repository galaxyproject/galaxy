<template>
    <div>
        <CellButton ref="buttonRef" title="Insert" :icon="faPlus" />
        <Popper v-if="buttonRef" :reference-el="buttonRef.$el" trigger="click" placement="right" mode="light">
            <DelayedInput class="p-1" :delay="100" placeholder="Search" @change="query = $event" />
            <div class="cell-add-categories overflow-auto">
                <div v-if="filteredTemplates.length > 0">
                    <div v-for="(category, categoryIndex) of filteredTemplates" :key="categoryIndex">
                        <hr class="solid m-0" />
                        <span class="d-flex justify-content-between">
                            <small class="my-1 mx-3 text-info">{{ category.name }}</small>
                        </span>
                        <div v-if="category.templates.length > 0" class="cell-add-options popper-close">
                            <CellOption
                                v-for="(option, optionIndex) of category.templates"
                                :key="optionIndex"
                                :title="option.title"
                                :description="option.description"
                                @click="$emit('click', { configure: false, toggle: true, ...option.cell })" />
                        </div>
                    </div>
                </div>
                <BAlert v-else class="m-1 p-1" variant="info" show> No results found for "{{ query }}". </BAlert>
            </div>
        </Popper>
    </div>
</template>

<script setup lang="ts">
import { faPlus } from "@fortawesome/free-solid-svg-icons";
import { BAlert } from "bootstrap-vue";
import { computed, ref } from "vue";

import { cellTemplates } from "./templates";
import type { CellType, TemplateCategory } from "./types";

import CellButton from "./CellButton.vue";
import CellOption from "./CellOption.vue";
import DelayedInput from "@/components/Common/DelayedInput.vue";
import Popper from "@/components/Popper/Popper.vue";

defineEmits<{
    (e: "click", cell: CellType): void;
}>();

const buttonRef = ref();
const query = ref("");

const filteredTemplates = computed(() => {
    const filteredCategories: Array<TemplateCategory> = [];
    cellTemplates.forEach((category) => {
        const matchedTemplates = category.templates.filter(
            (template) =>
                category.name.toLowerCase().includes(query.value.toLowerCase()) ||
                template.title.toLowerCase().includes(query.value.toLowerCase()) ||
                template.description.toLowerCase().includes(query.value.toLowerCase())
        );
        if (matchedTemplates.length > 0) {
            filteredCategories.push({
                name: category.name,
                templates: matchedTemplates,
            });
        }
    });
    return filteredCategories;
});
</script>

<style>
.cell-add-categories {
    max-height: 20rem;
    max-width: 15rem;
    min-width: 15rem;
}
</style>

<template>
    <div>
        <CellButton ref="buttonRef" title="Insert" :icon="faPlus" />
        <Popper v-if="buttonRef" :reference-el="buttonRef.$el" trigger="click" placement="right" mode="light">
            <DelayedInput class="p-1" :delay="100" placeholder="Search" @change="query = $event" />
            <div class="cell-dropdown overflow-auto">
                <div v-if="Object.keys(filteredTemplates).length > 0">
                    <div
                        v-for="(templates, categoryName) of filteredTemplates"
                        :key="categoryName"
                        class="cell-add-categories">
                        <hr class="solid m-0" />
                        <span class="d-flex justify-content-between">
                            <small class="my-1 mx-3 text-info">{{ categoryName }}</small>
                        </span>
                        <div v-if="templates.length > 0" class="cell-add-options popper-close">
                            <CellOption
                                v-for="(option, optionIndex) of templates"
                                :key="optionIndex"
                                :title="option.title"
                                :description="option.description"
                                :logo="option.logo"
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
import { computed, onMounted, type Ref, ref } from "vue";

import { getVisualizations } from "./services";
import cellTemplates from "./templates.yml";
import type { CellType, TemplateEntry } from "./types";

import CellButton from "./CellButton.vue";
import CellOption from "./CellOption.vue";
import DelayedInput from "@/components/Common/DelayedInput.vue";
import Popper from "@/components/Popper/Popper.vue";

defineEmits<{
    (e: "click", cell: CellType): void;
}>();

const buttonRef = ref();
const query = ref("");
const visualizations: Ref<Array<TemplateEntry>> = ref([]);

const allTemplates = computed(() => {
    const result = { ...(cellTemplates as Record<string, Array<TemplateEntry>>) };
    result["Visualization"] = visualizations.value;
    return result;
});

const filteredTemplates = computed(() => {
    const filteredCategories: Record<string, TemplateEntry[]> = {};
    Object.entries(allTemplates.value).forEach(([categoryName, templates]) => {
        const matchedTemplates = templates.filter(
            (template) =>
                categoryName.toLowerCase().includes(query.value.toLowerCase()) ||
                template.title.toLowerCase().includes(query.value.toLowerCase()) ||
                template.description.toLowerCase().includes(query.value.toLowerCase())
        );
        if (matchedTemplates.length > 0) {
            filteredCategories[categoryName] = matchedTemplates;
        }
    });
    return filteredCategories;
});

onMounted(async () => {
    visualizations.value = await getVisualizations();
});
</script>

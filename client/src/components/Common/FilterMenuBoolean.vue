<script setup lang="ts">
import { BFormGroup, BFormRadioGroup } from "bootstrap-vue";
import { computed } from "vue";

import type { ValidFilter } from "@/utils/filtering";

import GCheckbox from "@/components/BaseComponents/GCheckbox.vue";

type FilterType = string | boolean | undefined;

interface Props {
    name: string;
    filter: ValidFilter<any>;
    filters: {
        [k: string]: FilterType;
    };
    view?: "dropdown" | "popover" | "compact";
}

const props = withDefaults(defineProps<Props>(), {
    view: "dropdown",
});

const boolType = computed(() => props.filter.boolType || "default");
const isCheckbox = computed(() => boolType.value === "is" && props.view === "compact");

const options =
    boolType.value == "default"
        ? [
              { text: "Any", value: "any" },
              { text: "Yes", value: true },
              { text: "No", value: false },
          ]
        : [
              { text: "Yes", value: true },
              { text: "No", value: "any" },
          ];

const emit = defineEmits<{
    (e: "on-esc"): void;
    (e: "on-enter"): void;
    (e: "change", name: string, value: FilterType): void;
}>();

const value = computed({
    get: () => {
        const value = props.filters[props.name];
        return value !== undefined ? value : "any";
    },
    set: (newVal) => {
        const value = newVal !== null ? newVal : "any";
        emit("change", props.name, value);
    },
});
</script>

<template>
    <!-- eslint-disable-next-line vuejs-accessibility/no-static-element-interactions -->
    <div :class="{ 'd-flex': isCheckbox }" @keyup.enter="emit('on-enter')" @keyup.esc="emit('on-esc')">
        <small :class="{ 'mr-1': isCheckbox }">{{ props.filter.placeholder }}:</small>

        <div v-if="isCheckbox" :data-description="`filter ${props.name}`">
            <!-- value is "any" when unset, which is not a checked state -->
            <GCheckbox
                :aria-label="props.filter.placeholder"
                :model-value="value === true"
                @update:model-value="value = $event" />
        </div>
        <BFormGroup v-else class="m-0">
            <BFormRadioGroup
                v-model="value"
                :options="options"
                size="sm"
                buttons
                :data-description="`filter ${props.name}`" />
        </BFormGroup>
    </div>
</template>

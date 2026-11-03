<script setup lang="ts">
import { computed, ref, watch } from "vue";

import { useUid } from "@/composables/utils/uid";
import type { ValidFilter } from "@/utils/filtering";

import GCheckbox from "@/components/BaseComponents/GCheckbox.vue";
import GRadioGroup from "@/components/BaseComponents/GRadioGroup.vue";

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

const labelId = useUid("filter-menu-boolean-label-");

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

function filterValue() {
    const value = props.filters[props.name];
    return value !== undefined ? value : "any";
}

// FilterMenu stages changes in a non-reactive object until search, so the shown choice is kept here
const selected = ref<FilterType>(filterValue());

const value = computed({
    get: () => selected.value,
    set: (newVal) => {
        const value = newVal !== null ? newVal : "any";
        selected.value = value;
        emit("change", props.name, value);
    },
});

watch(
    () => props.filters,
    () => {
        selected.value = filterValue();
    },
);
</script>

<template>
    <!-- eslint-disable-next-line vuejs-accessibility/no-static-element-interactions -->
    <div :class="{ 'd-flex': isCheckbox }" @keyup.enter="emit('on-enter')" @keyup.esc="emit('on-esc')">
        <small :id="labelId" :class="{ 'mr-1': isCheckbox }">{{ props.filter.placeholder }}:</small>

        <div v-if="isCheckbox" :data-description="`filter ${props.name}`">
            <!-- value is "any" when unset, which is not a checked state -->
            <GCheckbox :aria-labelledby="labelId" :model-value="value === true" @update:model-value="value = $event" />
        </div>
        <GRadioGroup
            v-else
            v-model="value"
            buttons
            size="small"
            :aria-labelledby="labelId"
            :data-description="`filter ${props.name}`"
            :options="options" />
    </div>
</template>

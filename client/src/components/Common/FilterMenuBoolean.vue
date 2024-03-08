<script setup lang="ts">
import { BFormGroup, BFormRadioGroup } from "bootstrap-vue";
import { computed } from "vue";

import type { ValidFilter } from "@/utils/filtering";

type FilterType = string | boolean | undefined;

interface Props {
    name: string;
    filter: ValidFilter<any>;
    filters: {
        [k: string]: FilterType;
    };
}

const props = defineProps<Props>();

const boolType = computed(() => props.filter.boolType || "default");

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
    <div @keyup.enter="emit('on-enter')" @keyup.esc="emit('on-esc')">
        <small>{{ props.filter.placeholder }}:</small>

        <BFormGroup class="m-0">
            <BFormRadioGroup
                v-model="value"
                :options="options"
                size="sm"
                buttons
                :data-description="`filter ${props.name}`" />
        </BFormGroup>
    </div>
</template>

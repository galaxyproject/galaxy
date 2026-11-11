<script setup lang="ts">
import { faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

import localize from "@/utils/localization";

import type { FieldFilter, FilterOption } from "./configs/types";
import type { ColumnFilterChip } from "./useColumnFilters";

import GButton from "@/components/BaseComponents/GButton.vue";

defineProps<{
    chips: ColumnFilterChip[];
}>();

const emit = defineEmits<{
    (e: "remove", filter: FieldFilter, option: FilterOption): void;
}>();
</script>

<template>
    <div
        v-if="chips.length > 0"
        class="d-flex flex-wrap align-items-center"
        data-description="grid active column filters">
        <GButton
            v-for="chip in chips"
            :key="`${chip.filter.key}-${chip.option.id}`"
            class="mr-1 mb-1"
            size="small"
            outline
            color="blue"
            :title="localize('Remove this filter')"
            :data-description="`grid active column filter ${chip.filter.key}`"
            :data-option-id="chip.option.id"
            @click="emit('remove', chip.filter, chip.option)">
            <span>{{ chip.title }}: {{ chip.option.name }}</span>
            <FontAwesomeIcon :icon="faTimes" class="ml-1" />
        </GButton>
    </div>
</template>

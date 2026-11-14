<script setup lang="ts">
import { ref } from "vue";

import type Filtering from "@/utils/filtering";

import FilterMenu from "@/components/Common/FilterMenu.vue";
import DataDialogSearch from "@/components/SelectionDialog/DataDialogSearch.vue";

interface Props {
    filter: string;
    /** Renders the advanced FilterMenu instead of the plain search box. */
    filterClass?: Filtering<any>;
    loading?: boolean;
    name?: string;
    placeholder?: string;
}

const props = withDefaults(defineProps<Props>(), {
    filterClass: undefined,
    loading: false,
    name: "",
    placeholder: "",
});

const emit = defineEmits<{
    (e: "update:filter", filter: string): void;
}>();

const showAdvancedSearch = ref(false);
</script>

<template>
    <FilterMenu
        v-if="props.filterClass"
        v-model:show-advanced="showAdvancedSearch"
        :filter-text="props.filter"
        :name="props.name"
        class="w-100"
        :placeholder="props.placeholder"
        :filter-class="props.filterClass"
        :loading="props.loading"
        @update:filter-text="(v: string) => emit('update:filter', v)" />

    <DataDialogSearch
        v-else
        :model-value="props.filter"
        :title="props.placeholder"
        @update:model-value="(v: string) => emit('update:filter', v)" />
</template>

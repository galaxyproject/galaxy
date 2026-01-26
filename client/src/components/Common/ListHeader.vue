<script setup lang="ts">
import { faAngleDown, faAngleUp, faBars, faCog, faGripVertical } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BDropdown, BDropdownGroup, BDropdownItem, BFormCheckbox } from "bootstrap-vue";
import { computed, ref } from "vue";

import { type ListViewMode, useUserStore } from "@/stores/userStore";

import GButton from "@/components/BaseComponents/GButton.vue";
import GButtonGroup from "@/components/BaseComponents/GButtonGroup.vue";

type SortBy = string;

interface ColumnOption {
    key: string;
    label: string;
}

interface SortOption {
    value: string;
    label: string;
}

interface Props {
    listId: string;
    allSelected?: boolean;
    showSelectAll?: boolean;
    showViewToggle?: boolean;
    showSortOptions?: boolean;
    selectAllDisabled?: boolean;
    indeterminateSelected?: boolean;
    columnOptions?: ColumnOption[];
    visibleColumns?: string[];
    sortOptions?: SortOption[];
}

const props = withDefaults(defineProps<Props>(), {
    allSelected: false,
    showSelectAll: false,
    showViewToggle: false,
    showSortOptions: false,
    selectAllDisabled: false,
    indeterminateSelected: false,
    columnOptions: () => [],
    visibleColumns: () => [],
    sortOptions: () => [],
});

const emit = defineEmits<{
    (e: "select-all"): void;
    (e: "toggle-column", key: string): void;
    (e: "sort-changed", sortBy: string, sortDesc: boolean): void;
}>();

const userStore = useUserStore();

const sortDesc = ref(true);

// Default sort options for backward compatibility
const defaultSortOptions: SortOption[] = [
    { value: "name", label: "Name" },
    { value: "update_time", label: "Update time" },
];

// Use provided sortOptions or fall back to defaults
const effectiveSortOptions = computed(() => {
    return props.sortOptions.length > 0 ? props.sortOptions : defaultSortOptions;
});

const sortBy = ref<SortBy>(effectiveSortOptions.value[0]?.value || "update_time");
const currentListViewMode = computed(() => userStore.currentListViewPreferences[props.listId] || "grid");

function onSort(newSortBy: SortBy) {
    if (sortBy.value === newSortBy) {
        sortDesc.value = !sortDesc.value;
    } else {
        sortBy.value = newSortBy;
        sortDesc.value = true; // Reset to descending when changing sort field
    }
    emit("sort-changed", sortBy.value, sortDesc.value);
}

function isColumnVisible(key: string) {
    return props.visibleColumns.includes(key);
}

function onToggleColumn(key: string) {
    emit("toggle-column", key);
}

function onToggleView(newView: ListViewMode) {
    userStore.setListViewPreference(props.listId, newView);
}

defineExpose({
    sortBy,
    sortDesc,
});
</script>

<template>
    <div class="list-header">
        <div class="list-header-select-all">
            <slot name="select-all">
                <BFormCheckbox
                    v-if="showSelectAll"
                    id="list-header-select-all"
                    class="unselectable"
                    :disabled="selectAllDisabled"
                    :checked="allSelected"
                    :indeterminate="indeterminateSelected"
                    @change="emit('select-all')">
                    Select all
                </BFormCheckbox>
            </slot>
        </div>

        <div class="list-header-filters">
            <div v-if="showSortOptions">
                Sort by:
                <GButtonGroup>
                    <GButton
                        v-for="option in effectiveSortOptions"
                        :id="`sortby-${option.value}`"
                        :key="option.value"
                        tooltip
                        size="small"
                        :title="sortDesc ? `Sort by ${option.label} ascending` : `Sort by ${option.label} descending`"
                        :pressed="sortBy === option.value"
                        color="blue"
                        outline
                        @click="onSort(option.value)">
                        <FontAwesomeIcon v-show="sortBy === option.value" :icon="sortDesc ? faAngleDown : faAngleUp" />
                        {{ option.label }}
                    </GButton>
                </GButtonGroup>
            </div>

            <BDropdown
                v-if="columnOptions.length > 0"
                text="Columns"
                size="sm"
                variant="outline-primary"
                right
                no-caret>
                <template v-slot:button-content>
                    <FontAwesomeIcon :icon="faCog" fixed-width />
                </template>

                <BDropdownGroup header="Show/Hide Columns">
                    <BDropdownItem
                        v-for="column in columnOptions"
                        :key="column.key"
                        :disabled="column.key === 'name'"
                        @click="column.key !== 'name' && onToggleColumn(column.key)">
                        <BFormCheckbox
                            :checked="isColumnVisible(column.key)"
                            :disabled="column.key === 'name'"
                            @click.prevent>
                            {{ column.label }}
                        </BFormCheckbox>
                    </BDropdownItem>
                </BDropdownGroup>
            </BDropdown>

            <slot name="extra-filter" />
        </div>

        <div v-if="showViewToggle">
            Display:
            <GButtonGroup>
                <GButton
                    id="view-grid"
                    tooltip
                    title="Grid view"
                    size="small"
                    :pressed="currentListViewMode === 'grid'"
                    outline
                    color="blue"
                    @click="onToggleView('grid')">
                    <FontAwesomeIcon :icon="faGripVertical" />
                </GButton>

                <GButton
                    id="view-list"
                    tooltip
                    title="List view"
                    size="small"
                    :pressed="currentListViewMode === 'list'"
                    outline
                    color="blue"
                    @click="onToggleView('list')">
                    <FontAwesomeIcon :icon="faBars" />
                </GButton>
            </GButtonGroup>
        </div>
    </div>
</template>

<style scoped lang="scss">
.list-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin: 0.5rem 0;

    .list-header-filters {
        display: flex;
        gap: 1rem;
        flex-wrap: wrap;
        align-items: center;
    }
}
</style>

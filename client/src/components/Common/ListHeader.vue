<script setup lang="ts">
import { faAngleDown, faAngleUp, faBars, faGripVertical } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BFormCheckbox } from "bootstrap-vue";
import { computed, ref } from "vue";

import { defaultSortKeys, type SortKey } from "@/components/Common";
import { type ListViewMode, useUserStore } from "@/stores/userStore";

import GButton from "@/components/BaseComponents/GButton.vue";
import GButtonGroup from "@/components/BaseComponents/GButtonGroup.vue";

type SortBy = "create_time" | "update_time" | "name";

interface Props {
    listId: string;
    sortKeys?: SortKey[];
    allSelected?: boolean;
    haveSelected?: boolean;
    showSelectAll?: boolean;
    selectedItems?: string[];
    showViewToggle?: boolean;
    showSortOptions?: boolean;
    selectAllDisabled?: boolean;
    indeterminateSelected?: boolean;
    intermediateSelected?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    allSelected: false,
    showSelectAll: false,
    selectedItems: undefined,
    showViewToggle: false,
    showSortOptions: false,
    selectAllDisabled: false,
    indeterminateSelected: false,
    sortKeys: () => defaultSortKeys,
});

const emit = defineEmits<{
    (e: "select-all"): void;
}>();

const userStore = useUserStore();

const sortDesc = ref(true);
const sortBy = ref<SortBy>("update_time");
const currentListViewMode = computed(() => userStore.currentListViewPreferences[props.listId] || "grid");

function onSort(newSortBy: SortBy) {
    if (sortBy.value === newSortBy) {
        sortDesc.value = !sortDesc.value;
    } else {
        sortBy.value = newSortBy;
    }
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
                <BFormCheckbox
                    v-if="showSelectAll"
                    :checked="allSelected"
                    :intermediate="intermediateSelected"
                    @change="emit('select-all')" />

                Sort by:
                <GButtonGroup>
                    <GButton
                        v-for="sortKey in sortKeys"
                        :id="`sortby-${sortKey.key}`"
                        :key="`sortby-${sortKey.key}`"
                        tooltip
                        size="small"
                        :title="sortDesc ? `Sort by ${sortKey.label} ascending` : `Sort by ${sortKey.label} descending`"
                        :pressed="sortBy === sortKey.key"
                        color="blue"
                        outline
                        @click="onSort(sortKey.key)">
                        <FontAwesomeIcon v-show="sortBy === sortKey.key" :icon="sortDesc ? faAngleDown : faAngleUp" />
                        {{ sortKey.label }}
                    </GButton>
                </GButtonGroup>

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
    </div>
</template>

<style scoped lang="scss">
.list-header {
    display: flex;
    width: 100%;
    padding: 0 0.5rem 0.5rem;
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

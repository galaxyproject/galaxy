<script setup lang="ts">
import { faAngleDown, faAngleUp, faBars, faGripVertical } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BFormCheckbox } from "bootstrap-vue";
import { computed, ref } from "vue";

import { type ListViewMode, useUserStore } from "@/stores/userStore";

import GButton from "@/components/BaseComponents/GButton.vue";
import GButtonGroup from "@/components/BaseComponents/GButtonGroup.vue";

type SortBy = "create_time" | "update_time" | "name";

interface Props {
    listId: string;
    allSelected?: boolean;
    showSelectAll?: boolean;
    showViewToggle?: boolean;
    showSortOptions?: boolean;
    selectAllDisabled?: boolean;
    indeterminateSelected?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    allSelected: false,
    showSelectAll: false,
    showViewToggle: false,
    showSortOptions: false,
    selectAllDisabled: false,
    indeterminateSelected: false,
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
                Sort by:
                <GButtonGroup>
                    <GButton
                        id="sortby-name"
                        tooltip
                        size="small"
                        :title="sortDesc ? 'Sort by name ascending' : 'Sort by name descending'"
                        :pressed="sortBy === 'name'"
                        color="blue"
                        outline
                        @click="onSort('name')">
                        <FontAwesomeIcon v-show="sortBy === 'name'" :icon="sortDesc ? faAngleDown : faAngleUp" />
                        Name
                    </GButton>

                    <GButton
                        id="sortby-update-time"
                        tooltip
                        size="small"
                        :title="sortDesc ? 'Sort by update time ascending' : 'Sort by update time descending'"
                        :pressed="sortBy === 'update_time'"
                        color="blue"
                        outline
                        @click="onSort('update_time')">
                        <FontAwesomeIcon v-show="sortBy === 'update_time'" :icon="sortDesc ? faAngleDown : faAngleUp" />
                        Update time
                    </GButton>
                </GButtonGroup>
            </div>

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

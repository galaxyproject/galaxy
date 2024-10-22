<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faAngleDown, faAngleUp, faBars, faGripVertical } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, BFormCheckbox } from "bootstrap-vue";
import { computed, ref } from "vue";

import { defaultSortKeys, type ListView, type SortBy, type SortKey } from "@/components/Common";
import { useUserStore } from "@/stores/userStore";

library.add(faAngleDown, faAngleUp, faBars, faGripVertical);

interface Props {
    sortKeys?: SortKey[];
    allSelected?: boolean;
    haveSelected?: boolean;
    showSelectAll?: boolean;
    selectedItems?: string[];
    showViewToggle?: boolean;
    intermediateSelected?: boolean;
}

withDefaults(defineProps<Props>(), {
    selectedItems: undefined,
    sortKeys: () => defaultSortKeys,
});

const emit = defineEmits<{
    (e: "select-all"): void;
}>();

const userStore = useUserStore();

const sortDesc = ref(true);
const sortBy = ref<SortBy>("update_time");
const listViewMode = computed<ListView>(() => (userStore.preferredListViewMode as ListView) || "grid");

function onSort(newSortBy: SortBy) {
    if (sortBy.value === newSortBy) {
        sortDesc.value = !sortDesc.value;
    } else {
        sortBy.value = newSortBy;
    }
}

function onToggleView(newView: ListView) {
    userStore.setPreferredListViewMode(newView);
}

defineExpose({
    sortBy,
    sortDesc,
    listViewMode,
});
</script>

<template>
    <div class="list-header">
        <div class="list-header-filters">
            <BFormCheckbox
                v-if="showSelectAll"
                :checked="allSelected"
                :intermediate="intermediateSelected"
                @change="emit('select-all')" />

            Sort by:
            <BButtonGroup>
                <BButton
                    v-for="sortKey in sortKeys"
                    :id="`sortby-${sortKey.key}`"
                    :key="`sortby-${sortKey.key}`"
                    v-b-tooltip.hover
                    size="sm"
                    :title="sortDesc ? `Sort by ${sortKey.label} ascending` : `Sort by ${sortKey.label} descending`"
                    :pressed="sortBy === sortKey.key"
                    variant="outline-primary"
                    @click="onSort(sortKey.key)">
                    <FontAwesomeIcon v-show="sortBy === sortKey.key" :icon="sortDesc ? faAngleDown : faAngleUp" />
                    {{ sortKey.label }}
                </BButton>
            </BButtonGroup>

            <slot name="extra-filter" />
        </div>

        <div v-if="showViewToggle">
            Display:
            <BButtonGroup>
                <BButton
                    id="view-grid"
                    v-b-tooltip
                    title="Grid view"
                    size="sm"
                    :pressed="listViewMode === 'grid'"
                    variant="outline-primary"
                    @click="onToggleView('grid')">
                    <FontAwesomeIcon :icon="faGripVertical" />
                </BButton>

                <BButton
                    id="view-list"
                    v-b-tooltip
                    title="List view"
                    size="sm"
                    :pressed="listViewMode === 'list'"
                    variant="outline-primary"
                    @click="onToggleView('list')">
                    <FontAwesomeIcon :icon="faBars" />
                </BButton>
            </BButtonGroup>
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

    .list-header-filters {
        display: flex;
        gap: 0.25rem;
        flex-wrap: wrap;
        align-items: center;
    }
}
</style>

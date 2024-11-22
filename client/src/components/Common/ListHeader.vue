<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faAngleDown, faAngleUp, faBars, faGripVertical } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";
import { ref } from "vue";

import { useLocalPreferences } from "@/stores/localPreferencesStore";

library.add(faAngleDown, faAngleUp, faBars, faGripVertical);

type ListView = "grid" | "list";
type SortBy = "create_time" | "update_time" | "name";

interface Props {
    showViewToggle?: boolean;
}

withDefaults(defineProps<Props>(), {
    showViewToggle: false,
});

const { preferredListViewMode } = useLocalPreferences();

const sortDesc = ref(true);
const sortBy = ref<SortBy>("update_time");

function onSort(newSortBy: SortBy) {
    if (sortBy.value === newSortBy) {
        sortDesc.value = !sortDesc.value;
    } else {
        sortBy.value = newSortBy;
    }
}

function onToggleView(newView: ListView) {
    preferredListViewMode.value = newView;
}

defineExpose({
    sortBy,
    sortDesc,
    listViewMode: preferredListViewMode,
});
</script>

<template>
    <div class="list-header">
        <div class="list-header-filters">
            Sort by:
            <BButtonGroup>
                <BButton
                    id="sortby-name"
                    v-b-tooltip.hover
                    size="sm"
                    :title="sortDesc ? 'Sort by name ascending' : 'Sort by name descending'"
                    :pressed="sortBy === 'name'"
                    variant="outline-primary"
                    @click="onSort('name')">
                    <FontAwesomeIcon v-show="sortBy === 'name'" :icon="sortDesc ? faAngleDown : faAngleUp" />
                    Name
                </BButton>

                <BButton
                    id="sortby-update-time"
                    v-b-tooltip.hover
                    size="sm"
                    :title="sortDesc ? 'Sort by update time ascending' : 'Sort by update time descending'"
                    :pressed="sortBy === 'update_time'"
                    variant="outline-primary"
                    @click="onSort('update_time')">
                    <FontAwesomeIcon v-show="sortBy === 'update_time'" :icon="sortDesc ? faAngleDown : faAngleUp" />
                    Update time
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
                    :pressed="preferredListViewMode === 'grid'"
                    variant="outline-primary"
                    @click="onToggleView('grid')">
                    <FontAwesomeIcon :icon="faGripVertical" />
                </BButton>

                <BButton
                    id="view-list"
                    v-b-tooltip
                    title="List view"
                    size="sm"
                    :pressed="preferredListViewMode === 'list'"
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

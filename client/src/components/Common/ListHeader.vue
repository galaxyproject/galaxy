<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faAngleDown, faAngleUp, faBars, faGripVertical } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, BButtonGroup, BFormCheckbox } from "bootstrap-vue";
import { computed, ref } from "vue";

import { type ListViewMode, useUserStore } from "@/stores/userStore";

library.add(faAngleDown, faAngleUp, faBars, faGripVertical);

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
                    :disabled="selectAllDisabled"
                    :checked="allSelected"
                    :indeterminate="indeterminateSelected"
                    @change="emit('select-all')">
                    全选
                </BFormCheckbox>
            </slot>
        </div>

        <div class="list-header-filters">
            <div v-if="showSortOptions">
                排序方式:
                <BButtonGroup>
                    <BButton
                        id="sortby-name"
                        v-b-tooltip.hover
                        size="sm"
                        :title="sortDesc ? '按名称升序排序' : '按名称降序排序'"
                        :pressed="sortBy === 'name'"
                        variant="outline-primary"
                        @click="onSort('name')">
                        <FontAwesomeIcon v-show="sortBy === 'name'" :icon="sortDesc ? faAngleDown : faAngleUp" />
                        名称
                    </BButton>

                    <BButton
                        id="sortby-update-time"
                        v-b-tooltip.hover
                        size="sm"
                        :title="sortDesc ? '按更新时间升序排序' : '按更新时间降序排序'"
                        :pressed="sortBy === 'update_time'"
                        variant="outline-primary"
                        @click="onSort('update_time')">
                        <FontAwesomeIcon v-show="sortBy === 'update_time'" :icon="sortDesc ? faAngleDown : faAngleUp" />
                        更新时间
                    </BButton>
                </BButtonGroup>
            </div>

            <slot name="extra-filter" />
        </div>

        <div v-if="showViewToggle">
            显示方式:
            <BButtonGroup>
                <BButton
                    id="view-grid"
                    v-b-tooltip
                    title="网格视图"
                    size="sm"
                    :pressed="currentListViewMode === 'grid'"
                    variant="outline-primary"
                    @click="onToggleView('grid')">
                    <FontAwesomeIcon :icon="faGripVertical" />
                </BButton>

                <BButton
                    id="view-list"
                    v-b-tooltip
                    title="列表视图"
                    size="sm"
                    :pressed="currentListViewMode === 'list'"
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
    margin: 0.5rem 0;

    .list-header-filters {
        display: flex;
        gap: 1rem;
        flex-wrap: wrap;
        align-items: center;
    }
}
</style>

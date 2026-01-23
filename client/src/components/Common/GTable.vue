<script setup lang="ts" generic="T extends Record<string, any>">
import { faSort, faSortDown, faSortUp } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BFormCheckbox, BOverlay } from "bootstrap-vue";
import { computed, ref } from "vue";

import { useUid } from "@/composables/utils/uid";

import type {
    FieldAlignment,
    RowClickEvent,
    RowSelectEvent,
    SortChangeEvent,
    TableAction,
    TableEmptyState,
    TableField,
} from "./GTable.types";

import LoadingSpan from "@/components/LoadingSpan.vue";

interface Props {
    /** Unique identifier for the table
     * @default useUid("g-table-").value
     */
    id?: string;

    /** Table field definitions
     * @default []
     */
    fields?: TableField[];

    /** Table data items
     * @default []
     */
    items?: T[];

    /** Whether to show striped rows
     * @default true
     */
    striped?: boolean;

    /** Whether to show hover effect on rows
     * @default true
     */
    hover?: boolean;

    /** Whether to show borders
     * @default false
     */
    bordered?: boolean;

    /** Whether rows are clickable
     * @default false
     */
    clickableRows?: boolean;

    /** Whether to show selection checkboxes
     * @default false
     */
    selectable?: boolean;

    /** Array of selected item indices
     * @default []
     */
    selectedItems?: number[];

    /** Current sort field key
     * @default ""
     */
    sortBy?: string;

    /** Whether sorting in descending order
     * @default false
     */
    sortDesc?: boolean;

    /** Whether to disable local sorting (for server-side sorting)
     * @default false
     */
    noLocalSorting?: boolean;

    /** Whether to reset sort on column click
     * @default false
     */
    noSortReset?: boolean;

    /** Whether the table is in loading state
     * @default false
     */
    loading?: boolean;

    /** Loading message to display
     * @default "Loading..."
     */
    loadingMessage?: string;

    /** Whether to show overlay loading (for sorting/filtering operations)
     * @default false
     */
    overlayLoading?: boolean;

    /** Whether to show load-more loading indicator at bottom (for pagination/scroll)
     * @default false
     */
    loadMoreLoading?: boolean;

    /** Load-more loading message
     * @default "Loading more..."
     */
    loadMoreMessage?: string;

    /** Empty state configuration
     * @default { message: "No data available" }
     */
    emptyState?: TableEmptyState;

    /** Additional CSS classes for the table container
     * @default ""
     */
    containerClass?: string | string[];

    /** Additional CSS classes for the table element
     * @default ""
     */
    tableClass?: string | string[];

    /** Table actions displayed above the table
     * @default []
     */
    actions?: TableAction[];

    /** Whether to show select all checkbox in header
     * @default false
     */
    showSelectAll?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    id: () => useUid("g-table-").value,
    fields: () => [],
    items: () => [],
    striped: true,
    hover: true,
    bordered: false,
    clickableRows: false,
    selectable: false,
    selectedItems: () => [],
    sortBy: "",
    sortDesc: false,
    noLocalSorting: false,
    noSortReset: false,
    loading: false,
    loadingMessage: "Loading...",
    overlayLoading: false,
    loadMoreLoading: false,
    loadMoreMessage: "Loading more...",
    emptyState: () => ({ message: "No data available" }),
    containerClass: "",
    tableClass: "",
    actions: () => [],
    showSelectAll: false,
});

/**
 * Events emitted by the GTable component
 */
const emit = defineEmits<{
    /** Emitted when sort changes
     * @event sort-changed
     */
    (e: "sort-changed", event: SortChangeEvent): void;

    /** Emitted when a row is clicked
     * @event row-click
     */
    (e: "row-click", event: RowClickEvent<T>): void;

    /** Emitted when a row is selected/deselected
     * @event row-select
     */
    (e: "row-select", event: RowSelectEvent<T>): void;

    /** Emitted when select all is toggled
     * @event select-all
     */
    (e: "select-all", selected: boolean): void;
}>();

// Internal state for local sorting
const localSortBy = ref<string | undefined>(props.sortBy);
const localSortDesc = ref(props.sortDesc);

// Computed sorted items
const sortedItems = computed(() => {
    if (props.noLocalSorting || !localSortBy.value) {
        return props.items;
    }

    const sorted = [...props.items];
    const sortKey = localSortBy.value;

    sorted.sort((a, b) => {
        const aVal = a[sortKey];
        const bVal = b[sortKey];

        if (aVal === bVal) {
            return 0;
        }
        if (aVal === null || aVal === undefined) {
            return 1;
        }
        if (bVal === null || bVal === undefined) {
            return -1;
        }

        const comparison = aVal < bVal ? -1 : 1;
        return localSortDesc.value ? -comparison : comparison;
    });

    return sorted;
});

// Check if all items are selected
const allSelected = computed(() => {
    return props.items.length > 0 && props.selectedItems.length === props.items.length;
});

// Check if some items are selected
const someSelected = computed(() => {
    return props.selectedItems.length > 0 && props.selectedItems.length < props.items.length;
});

/**
 * Handle column header click for sorting
 */
function onHeaderClick(field: TableField) {
    if (!field.sortable) {
        return;
    }

    if (localSortBy.value === field.key) {
        if (!props.noSortReset && localSortDesc.value) {
            // Reset sort
            localSortBy.value = undefined;
            localSortDesc.value = false;
        } else {
            // Toggle sort direction
            localSortDesc.value = !localSortDesc.value;
        }
    } else {
        // New sort field
        localSortBy.value = field.key;
        localSortDesc.value = false;
    }

    emit("sort-changed", {
        sortBy: localSortBy.value || "",
        sortDesc: localSortDesc.value,
    });
}

/**
 * Get sort icon for a field
 */
function getSortIcon(field: TableField) {
    if (!field.sortable) {
        return null;
    }

    if (localSortBy.value !== field.key) {
        return faSort;
    }

    return localSortDesc.value ? faSortDown : faSortUp;
}

/**
 * Handle row click
 */
function onRowClick(item: T, index: number, event: MouseEvent | KeyboardEvent) {
    if (!props.clickableRows) {
        return;
    }

    emit("row-click", { item, index, event });
}

/**
 * Handle row selection toggle
 */
function onRowSelect(item: T, index: number) {
    const isSelected = props.selectedItems.includes(index);
    emit("row-select", { item, index, selected: !isSelected });
}

/**
 * Handle select all toggle
 */
function onSelectAll() {
    emit("select-all", !allSelected.value);
}

/**
 * Get cell value with optional formatter
 */
function getCellValue(item: T, field: TableField) {
    const value = item[field.key];

    if (field.formatter) {
        return field.formatter(value, field.key, item);
    }

    return value;
}

/**
 * Get alignment class for a field
 */
function getAlignmentClass(align?: FieldAlignment) {
    if (!align || align === "left") {
        return "";
    }
    return `text-${align}`;
}

/**
 * Check if row is selected
 */
function isRowSelected(index: number) {
    return props.selectedItems.includes(index);
}

/**
 * Helper functions for generating consistent element IDs
 */
const getElementId = (tableId: string, element: string) => `g-table-${element}-${tableId}`;
const getFieldId = (tableId: string, fieldKey: string) => `g-table-field-${fieldKey}-${tableId}`;
const getRowId = (tableId: string, index: number) => `g-table-row-${index}-${tableId}`;
const getCellId = (tableId: string, fieldKey: string, index: number) => `g-table-cell-${fieldKey}-${index}-${tableId}`;
</script>

<template>
    <div :id="`g-table-container-${props.id}`" class="w-100" :class="containerClass">
        <!-- Actions toolbar -->
        <div v-if="props.actions.length > 0" :id="getElementId(props.id, 'actions')" class="g-table-actions mb-2">
            <slot name="actions">
                <!-- Custom actions can be added here -->
            </slot>
        </div>

        <!-- Table wrapper -->
        <BOverlay :show="overlayLoading" rounded="sm" class="position-relative w-100">
            <div :id="`g-table-wrapper-${props.id}`" class="position-relative w-100">
                <table
                    :id="`g-table-${props.id}`"
                    class="g-table table w-100 mb-0"
                    :class="[
                        { 'table-striped': striped },
                        { 'table-hover': hover },
                        { 'table-bordered': bordered },
                        tableClass,
                    ]">
                    <thead>
                        <tr>
                            <!-- Select all checkbox column -->
                            <!-- <th v-if="selectable && showSelectAll" class="g-table-select-column">
                                <BFormCheckbox
                                    :id="getElementId(props.id, 'select-all')"
                                    v-b-tooltip.hover.noninteractive
                                    :checked="allSelected"
                                    :indeterminate="someSelected"
                                    title="Select all"
                                    @change="onSelectAll" />
                            </th> -->
                            <!-- <th v-else-if="selectable" class="g-table-select-column"></th> -->
                            <th lass="g-table-select-column"></th>

                            <!-- Field columns -->
                            <th
                                v-for="field in props.fields"
                                :id="getFieldId(props.id, field.key)"
                                :key="field.key"
                                :class="[
                                    field.headerClass,
                                    getAlignmentClass(field.align),
                                    { 'g-table-sortable': field.sortable },
                                    { 'g-table-sorted': localSortBy === field.key },
                                    { 'hide-on-small': field.hideOnSmall },
                                ]"
                                :style="field.width ? { width: field.width } : undefined"
                                @click="onHeaderClick(field)">
                                <div class="d-flex align-items-center justify-content-between">
                                    <slot :name="`head(${field.key})`" :field="field">
                                        <span>{{ field.label || field.key }}</span>
                                    </slot>
                                    <FontAwesomeIcon
                                        v-if="field.sortable && getSortIcon(field)"
                                        :icon="getSortIcon(field)"
                                        :class="{ 'text-muted': localSortBy !== field.key }"
                                        class="ml-1" />
                                </div>
                            </th>

                            <!-- Actions column header (if slot provided) -->
                            <th v-if="$slots.actions || $scopedSlots.actions" class="g-table-actions-column">
                                <slot name="head(actions)">Actions</slot>
                            </th>
                        </tr>
                    </thead>

                    <tbody v-if="sortedItems.length > 0">
                        <tr
                            v-for="(item, index) in sortedItems"
                            :id="getRowId(props.id, index)"
                            :key="index"
                            :class="{
                                'g-table-row-clickable': clickableRows,
                                'g-table-row-selected': isRowSelected(index),
                            }"
                            @click="onRowClick(item, index, $event)">
                            <!-- Selection checkbox column -->
                            <td v-if="selectable" class="g-table-select-column">
                                <BFormCheckbox
                                    :id="`${getRowId(props.id, index)}-select`"
                                    v-b-tooltip.hover.noninteractive
                                    :checked="isRowSelected(index)"
                                    title="Select row"
                                    @click.stop
                                    @change="onRowSelect(item, index)" />
                            </td>

                            <!-- Data columns -->
                            <td
                                v-for="field in props.fields"
                                :id="getCellId(props.id, field.key, index)"
                                :key="field.key"
                                :class="[
                                    field.cellClass,
                                    field.class,
                                    getAlignmentClass(field.align),
                                    { 'hide-on-small': field.hideOnSmall },
                                ]">
                                <slot :name="`cell(${field.key})`" :value="item[field.key]" :item="item" :index="index">
                                    <!-- eslint-disable-next-line vue/no-v-html -->
                                    <span v-if="field.html" v-html="getCellValue(item, field)"></span>
                                    <span v-else>{{ getCellValue(item, field) }}</span>
                                </slot>
                            </td>

                            <!-- Actions column -->
                            <td v-if="$slots.actions || $scopedSlots.actions" class="g-table-actions-column">
                                <slot name="actions" :item="item" :index="index"></slot>
                            </td>
                        </tr>
                    </tbody>
                </table>

                <!-- Load more loading indicator -->
                <div v-if="loadMoreLoading && sortedItems.length > 0" class="g-table-load-more py-3 text-center">
                    <LoadingSpan :message="props.loadMoreMessage" />
                </div>
            </div>
        </BOverlay>
    </div>
</template>

<style scoped lang="scss">
@import "@/style/scss/theme/blue.scss";
@import "@/style/scss/_breakpoints.scss";

// Essential custom styles that cannot be replaced with utility classes
.g-table {
    thead th {
        position: sticky;
        top: 0;
        background-color: $body-bg;
        z-index: 10;
        border-bottom: 2px solid $brand-secondary;
        font-weight: 600;
        padding: 0.75rem;

        &.g-table-sortable {
            cursor: pointer;
            user-select: none;

            &:hover {
                background-color: lighten($brand-light, 0.5);
            }
        }

        &.g-table-sorted {
            background-color: $brand-light;
        }
    }

    tbody {
        tr {
            &.g-table-row-clickable {
                cursor: pointer;

                &:hover {
                    background-color: lighten($brand-light, 0.5);
                }
            }

            &.g-table-row-selected {
                background-color: $brand-light;
            }
        }

        td {
            padding: 0.75rem;
            vertical-align: middle;
        }
    }

    .g-table-select-column {
        width: 40px;
        text-align: center;
    }

    .g-table-actions-column {
        width: 60px;
        text-align: center;
    }

    @media (max-width: $breakpoint-sm) {
        .hide-on-small {
            display: none;
        }
    }
}

.g-table-load-more {
    border-top: 1px solid $brand-secondary;
}
</style>

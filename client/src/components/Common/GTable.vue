<script setup lang="ts" generic="T extends Record<string, any>">
import { faEllipsisV, faSort, faSortDown, faSortUp } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BDropdown, BDropdownItem, BFormCheckbox, BOverlay } from "bootstrap-vue";
import { computed, ref } from "vue";

import type { BootstrapSize } from "@/components/Common";
import { useUid } from "@/composables/utils/uid";

import type {
    FieldAlignment,
    RowClickEvent,
    RowIcon,
    RowSelectEvent,
    TableAction,
    TableEmptyState,
    TableField,
} from "./GTable.types";

import LoadingSpan from "@/components/LoadingSpan.vue";

interface Props {
    /**
     * Unique identifier for the table
     * @default useUid("g-table-").value
     */
    id?: string;

    /**
     * Table actions displayed above the table
     * @default []
     */
    actions?: TableAction[];

    /**
     * Whether to show borders
     * @default false
     */
    bordered?: boolean;

    /**
     * Whether to place table caption at the top (above the table)
     * @default false
     */
    captionTop?: boolean;

    /**
     * Whether rows are clickable
     * @default false
     */
    clickableRows?: boolean;

    /**
     * Whether to use compact table spacing (BootstrapVue `small`)
     * @default false
     */
    compact?: boolean;

    /**
     * Additional CSS classes for the table container
     * @default ""
     */
    containerClass?: string | string[];

    /**
     * Current page number for pagination (1-based)
     * @default undefined
     */
    currentPage?: number;

    /**
     * Empty state configuration
     * @default { message: "No data available" }
     */
    emptyState?: TableEmptyState;

    /**
     * Table field definitions
     * @default []
     */
    fields?: TableField[];

    /**
     * Filter string to filter items
     * @default ""
     */
    filter?: string;

    /**
     * Array of field keys to exclude from filtering
     * @default undefined
     */
    filterIgnoredFields?: string[];

    /**
     * Array of field keys to include in filtering
     * If specified, only these fields will be searched
     * @default undefined
     */
    filterIncludedFields?: string[];

    /**
     * Whether to use fixed table layout (BootstrapVue `fixed`)
     * @default false
     */
    fixed?: boolean;

    /**
     * Whether to show hover effect on rows
     * @default true
     */
    hover?: boolean;

    /**
     * Whether to hide the table header
     * @default false
     */
    hideHeader?: boolean;

    /**
     * Table data items
     * @default []
     */
    items?: T[];

    /**
     * Whether the table is in loading state
     * @default false
     */
    loading?: boolean;

    /**
     * Loading message to display
     * @default "Loading..."
     */
    loadingMessage?: string;

    /**
     * Whether to show load-more loading indicator at bottom (for pagination/scroll)
     * @default false
     */
    loadMoreLoading?: boolean;

    /**
     * Load-more loading message
     * @default "Loading more..."
     */
    loadMoreMessage?: string;

    /**
     * Whether to show overlay loading (for sorting/filtering operations)
     * @default false
     */
    overlayLoading?: boolean;

    /**
     * Whether to use local filtering (client-side) or rely on external filtering (server-side)
     * @default true
     */
    localFiltering?: boolean;

    /**
     * Whether to use local sorting (client-side) or rely on external sorting (server-side)
     * @default true
     */
    localSorting?: boolean;

    /**
     * Number of items per page for pagination
     * @default undefined
     */
    perPage?: number;

    /**
     * Whether to show striped rows
     * @default true
     */
    striped?: boolean;

    /**
     * Whether to show selection checkboxes
     * @default false
     */
    selectable?: boolean;

    /**
     * Array of selected item indices
     * @default []
     */
    selectedItems?: number[];

    /**
     * Whether to show the empty state message when no items are available
     * @default false
     */
    showEmpty?: boolean;

    /**
     * Current sort field key
     * @default ""
     */
    sortBy?: string;

    /**
     * Whether sorting in descending order
     * @default false
     */
    sortDesc?: boolean;

    /**
     * Whether to show select all checkbox in header
     * @default false
     */
    showSelectAll?: boolean;

    /**
     * Whether to use responsive stacked layout on small screens
     * @default false
     */
    stacked?: boolean | BootstrapSize;

    /**
     * Row status icon getter - renders icon inline with first data column
     * Return undefined to skip icon for a row
     * @default undefined
     */
    statusIcon?: (item: T, index: number) => RowIcon | undefined;

    /**
     * Whether to use sticky header with optional max height (e.g. "300px")
     * @default false
     */
    stickyHeader?: boolean | string;

    /**
     * Additional CSS classes for the table element
     * @default ""
     */
    tableClass?: string | string[];
}

const props = withDefaults(defineProps<Props>(), {
    id: () => useUid("g-table-").value,
    actions: undefined,
    bordered: false,
    captionTop: false,
    clickableRows: false,
    compact: false,
    containerClass: "",
    currentPage: undefined,
    emptyState: () => ({ message: "No data available" }),
    fields: () => [],
    filter: "",
    filterIgnoredFields: undefined,
    filterIncludedFields: undefined,
    fixed: false,
    hover: true,
    hideHeader: false,
    items: () => [],
    loading: false,
    loadingMessage: "Loading...",
    loadMoreLoading: false,
    loadMoreMessage: "Loading more...",
    localFiltering: true,
    localSorting: true,
    overlayLoading: false,
    perPage: undefined,
    selectable: false,
    selectedItems: () => [],
    showEmpty: false,
    showSelectAll: false,
    sortBy: "",
    sortDesc: false,
    striped: true,
    stacked: false,
    statusIcon: undefined,
    stickyHeader: false,
    tableClass: "",
});

/**
 * Events emitted by the GTable component
 */
const emit = defineEmits<{
    /**
     * Emitted when items are filtered
     * @event filtered
     */
    (e: "filtered", filteredItems: T[]): void;

    /**
     * Emitted when sort changes
     * @event sort-changed
     */
    (e: "sort-changed", sortBy: string, sortDesc: boolean): void;

    /**
     * Emitted when select all checkbox is toggled
     * @event select-all
     */
    (e: "select-all"): void;

    /**
     * Emitted when a row is selected/deselected
     * @event row-select
     */
    (e: "row-select", event: RowSelectEvent<T>): void;

    /**
     * Emitted when a row is clicked
     * @event row-click
     */
    (e: "row-click", event: RowClickEvent<T>): void;
}>();

const sortBy = ref<string>(props.sortBy || "update_time");
const sortDesc = ref<boolean>(props.sortDesc || true);
const expandedRows = ref<Set<number>>(new Set());

const stackedClass = computed(() => {
    if (!props.stacked) {
        return undefined;
    }
    if (props.stacked === true) {
        return "g-table-stacked";
    }
    return `g-table-stacked-${props.stacked}`;
});

const stickyHeaderMaxHeight = computed(() => {
    if (!props.stickyHeader) {
        return undefined;
    }
    return props.stickyHeader === true ? "300px" : props.stickyHeader;
});

const paginatedLocalItems = computed(() => {
    if (!props.currentPage || !props.perPage) {
        return localItems.value;
    }

    const startIndex = (props.currentPage - 1) * props.perPage;
    return localItems.value.slice(startIndex, startIndex + props.perPage);
});

const localItems = computed(() => {
    let items = props.items || [];

    // If local sorting is disabled, return items as-is
    if (!props.localSorting) {
        return items;
    }

    // Apply local filtering if enabled and filter string is provided
    if (props.localFiltering && props.filter && props.filter.trim() !== "") {
        const filterLower = props.filter.toLowerCase().trim();
        items = items.filter((item) => {
            // Search through specified fields based on filterIncludedFields and filterIgnoredFields
            return Object.entries(item).some(([key, value]) => {
                // Skip if field is in ignored list
                if (props.filterIgnoredFields && props.filterIgnoredFields.includes(key)) {
                    return false;
                }

                // Skip if included list is specified and field is not in it
                if (props.filterIncludedFields && !props.filterIncludedFields.includes(key)) {
                    return false;
                }

                // Skip null/undefined values
                if (value == null) {
                    return false;
                }

                return String(value).toLowerCase().includes(filterLower);
            });
        });

        // Emit filtered event with the filtered items
        emit("filtered", items);
    }

    // If no sort field is set, return items as-is
    if (!sortBy.value) {
        return items;
    }

    // Create a shallow copy to avoid mutating the original array
    const sortedItems = [...items];

    // Find the field definition for the current sort key
    const field = props.fields.find((f) => f.key === sortBy.value);

    // Sort the items
    sortedItems.sort((a, b) => {
        let aVal = a[sortBy.value];
        let bVal = b[sortBy.value];

        // Apply formatter if available
        if (field?.formatter) {
            aVal = field.formatter(aVal, sortBy.value, a);
            bVal = field.formatter(bVal, sortBy.value, b);
        }

        // Handle null/undefined values
        if (aVal == null && bVal == null) {
            return 0;
        }
        if (aVal == null) {
            return 1;
        }
        if (bVal == null) {
            return -1;
        }

        // Compare values
        let comparison = 0;
        if (typeof aVal === "string" && typeof bVal === "string") {
            comparison = aVal.localeCompare(bVal);
        } else if (typeof aVal === "number" && typeof bVal === "number") {
            comparison = aVal - bVal;
        } else {
            // Convert to strings for comparison
            comparison = String(aVal).localeCompare(String(bVal));
        }

        return sortDesc.value ? -comparison : comparison;
    });

    return sortedItems;
});

const selectAllDisabled = computed(() => {
    return props.selectable && localItems.value.length === 0;
});
const indeterminateSelected = computed(() => {
    return props.selectable && props.selectedItems.length > 0 && props.selectedItems.length < localItems.value.length;
});
const allSelected = computed(() => {
    return props.selectable && localItems.value.length > 0 && props.selectedItems.length === localItems.value.length;
});

/**
 * Get the global index for a paginated item
 */
function getGlobalIndex(paginatedIndex: number): number {
    if (!props.currentPage || !props.perPage) {
        return paginatedIndex;
    }
    return (props.currentPage - 1) * props.perPage + paginatedIndex;
}

/**
 * Handle column header click for sorting
 */
function onHeaderClick(field: TableField) {
    if (!field.sortable) {
        return;
    }

    if (sortBy.value === field.key) {
        sortDesc.value = !sortDesc.value;
    } else {
        sortBy.value = field.key;
        sortDesc.value = false;
    }

    emit("sort-changed", sortBy.value || "", sortDesc.value);
}

/**
 * Get sort icon for a field
 */
function getSortIcon(field: TableField) {
    if (!field.sortable) {
        return null;
    }

    if (sortBy.value !== field.key) {
        return faSort;
    }

    return sortDesc.value ? faSortDown : faSortUp;
}

/**
 * Handle row click
 */
function onRowClick(item: T, index: number, event: MouseEvent | KeyboardEvent) {
    if (!props.clickableRows) {
        return;
    }

    emit("row-click", { item, index, event, toggleDetails: () => toggleRowDetails(index) });
}

function onSelectAll(selected: boolean) {
    emit("select-all");
}

/**
 * Handle row selection toggle
 */
function onRowSelect(item: T, index: number) {
    const isSelected = props.selectedItems.includes(index);
    emit("row-select", { item, index, selected: !isSelected });
}

/**
 * Check if row details are expanded
 */
function isRowExpanded(index: number) {
    return expandedRows.value.has(index);
}

/**
 * Toggle row details expansion
 */
function toggleRowDetails(index: number) {
    if (expandedRows.value.has(index)) {
        expandedRows.value.delete(index);
    } else {
        expandedRows.value.add(index);
    }
    // Trigger reactivity
    expandedRows.value = new Set(expandedRows.value);
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
 * Get text alignment class for header labels
 */
function getTextAlignmentClass(align?: FieldAlignment) {
    if (!align || align === "left") {
        return "";
    }
    return `text-${align}`;
}

/**
 * Get alignment class for body cells
 */
function getAlignmentClass(align?: FieldAlignment) {
    if (!align || align === "left") {
        return "";
    }
    return `text-${align}`;
}

/**
 * Get cell variant class for Bootstrap color variants (e.g., "success", "danger", "info")
 * Supports the _cellVariants convention from b-table for backward compatibility
 */
function getCellVariantClass(item: T, field: TableField) {
    const cellVariants = item._cellVariants as Record<string, string> | undefined;
    if (!cellVariants || !cellVariants[field.key]) {
        return undefined;
    }
    return `table-${cellVariants[field.key]}`;
}

/**
 * Check if row is selected
 */
function isRowSelected(index: number) {
    return props.selectedItems.includes(index);
}

/**
 * Get status icon for a row
 */
function getStatusIcon(item: T, index: number): RowIcon | undefined {
    return props.statusIcon?.(item, index);
}

/**
 * Get icon props for FontAwesomeIcon component
 * Computes icon attributes once per call
 */
function getIconProps(item: T, index: number) {
    const icon = getStatusIcon(item, index);
    if (!icon) {
        return {};
    }
    return {
        icon: icon.icon,
        class: [icon.class],
        title: icon.title,
        spin: icon.spin,
        size: icon.size,
    };
}

/**
 * Helper functions for generating consistent element IDs
 */
const getFieldId = (tableId: string, fieldKey: string) => `g-table-field-${fieldKey}-${tableId}`;
const getRowId = (tableId: string, index: number) => `g-table-row-${index}-${tableId}`;
const getCellId = (tableId: string, fieldKey: string, index: number) => `g-table-cell-${fieldKey}-${index}-${tableId}`;

/**
 * Refresh the table - useful for manual recalculation of computed properties
 */
function refresh() {
    // Force reactivity by re-assigning the expanded rows set
    expandedRows.value = new Set(expandedRows.value);
}

/**
 * Expose refresh method to parent components
 */
defineExpose({
    refresh,
});
</script>

<template>
    <div :id="`g-table-container-${props.id}`" class="g-table-container" :class="containerClass">
        <!-- Table wrapper -->
        <BOverlay :show="overlayLoading" rounded="sm" class="position-relative w-100">
            <div
                :id="`g-table-wrapper-${props.id}`"
                class="position-relative w-100"
                :class="{ 'g-table-sticky-header': props.stickyHeader }">
                <table
                    :id="`g-table-${props.id}`"
                    class="g-table table w-100 mb-0"
                    :class="[
                        { 'table-striped': striped },
                        { 'table-hover': hover },
                        { 'table-bordered': bordered },
                        { 'g-table-compact': compact },
                        { 'g-table-fixed': fixed },
                        { 'caption-top': captionTop },
                        stackedClass,
                        tableClass,
                    ]">
                    <caption v-if="$slots['table-caption']" :class="{ 'caption-top': captionTop }">
                        <slot name="table-caption" />
                    </caption>

                    <thead v-if="!props.hideHeader">
                        <tr>
                            <th v-if="selectable" class="g-table-select-column">
                                <slot name="head-select">
                                    <BFormCheckbox
                                        v-if="showSelectAll"
                                        :id="`g-table-select-all-${props.id}`"
                                        v-b-tooltip.hover.noninteractive
                                        :disabled="selectAllDisabled"
                                        :checked="allSelected"
                                        :indeterminate="indeterminateSelected"
                                        title="Select all for bulk actions"
                                        @click.stop
                                        @change="onSelectAll($event)" />
                                </slot>
                            </th>

                            <!-- Field columns -->
                            <th
                                v-for="field in props.fields"
                                :id="getFieldId(props.id, field.key)"
                                :key="field.key"
                                :class="[
                                    field.headerClass,
                                    { 'g-table-sortable': field.sortable },
                                    { 'g-table-sorted': sortBy === field.key },
                                    { 'hide-on-small': field.hideOnSmall },
                                ]"
                                :style="field.width ? { width: field.width, minWidth: field.width } : undefined"
                                @click="onHeaderClick(field)">
                                <div class="d-flex align-items-center">
                                    <div class="flex-grow-1" :class="getTextAlignmentClass(field.align)">
                                        <slot :name="`head(${field.key})`" :field="field">
                                            {{ field.label ?? field.key }}
                                        </slot>
                                    </div>
                                    <FontAwesomeIcon
                                        v-if="field.sortable && getSortIcon(field)"
                                        :icon="getSortIcon(field)"
                                        :class="{ 'g-table-sort-icon': sortBy !== field.key }"
                                        class="ml-1 flex-shrink-0" />
                                </div>
                            </th>

                            <th v-if="props.actions" class="g-table-actions-column">
                                <slot name="head-actions">Actions</slot>
                            </th>
                        </tr>
                    </thead>

                    <tbody>
                        <tr v-if="props.showEmpty && !props.items.length">
                            <td :colspan="(selectable ? 1 : 0) + props.fields.length + (props.actions ? 1 : 0)">
                                <slot name="empty">
                                    <BAlert v-if="!loading" variant="info" show class="w-100 m-0">
                                        {{ props.emptyState?.message ?? "No data available" }}
                                    </BAlert>
                                </slot>
                            </td>
                        </tr>

                        <template v-for="(item, paginatedIndex) in paginatedLocalItems">
                            <template>
                                <tr
                                    :id="getRowId(props.id, getGlobalIndex(paginatedIndex))"
                                    :key="`tr` + getGlobalIndex(paginatedIndex)"
                                    :class="{
                                        'g-table-row-clickable': clickableRows,
                                        'g-table-row-selected': isRowSelected(getGlobalIndex(paginatedIndex)),
                                    }"
                                    @click="onRowClick(item, getGlobalIndex(paginatedIndex), $event)">
                                    <!-- Selection checkbox column -->
                                    <td v-if="selectable" class="g-table-select-column">
                                        <BFormCheckbox
                                            :id="`${getRowId(props.id, getGlobalIndex(paginatedIndex))}-select`"
                                            v-b-tooltip.hover.noninteractive
                                            :checked="isRowSelected(getGlobalIndex(paginatedIndex))"
                                            title="Select for bulk actions"
                                            @click.stop
                                            @change="onRowSelect(item, getGlobalIndex(paginatedIndex))" />
                                    </td>

                                    <!-- Data columns -->
                                    <td
                                        v-for="(field, fieldIndex) in props.fields"
                                        :id="getCellId(props.id, field.key, getGlobalIndex(paginatedIndex))"
                                        :key="field.key"
                                        :data-label="field.label ?? field.key"
                                        :class="[
                                            field.cellClass,
                                            field.class,
                                            getAlignmentClass(field.align),
                                            getCellVariantClass(item, field),
                                            { 'hide-on-small': field.hideOnSmall },
                                        ]">
                                        <template
                                            v-if="
                                                fieldIndex === 0 && getStatusIcon(item, getGlobalIndex(paginatedIndex))
                                            ">
                                            <FontAwesomeIcon
                                                v-if="getStatusIcon(item, getGlobalIndex(paginatedIndex))"
                                                v-b-tooltip.hover.noninteractive
                                                v-bind="getIconProps(item, getGlobalIndex(paginatedIndex))"
                                                fixed-width />
                                        </template>

                                        <slot
                                            :name="`cell(${field.key})`"
                                            :value="item[field.key]"
                                            :item="item"
                                            :index="getGlobalIndex(paginatedIndex)"
                                            :toggle-details="() => toggleRowDetails(getGlobalIndex(paginatedIndex))">
                                            <span>{{ getCellValue(item, field) }}</span>
                                        </slot>
                                    </td>

                                    <!-- Actions column -->
                                    <td v-if="props.actions" class="g-table-actions-column">
                                        <slot name="actions" :item="item" :index="getGlobalIndex(paginatedIndex)">
                                            <BDropdown
                                                v-b-tooltip.hover.noninteractive
                                                no-caret
                                                right
                                                title="More actions"
                                                variant="link"
                                                size="lg"
                                                toggle-class="text-decoration-none p-0"
                                                @click.stop>
                                                <template v-slot:button-content>
                                                    <FontAwesomeIcon :icon="faEllipsisV" fixed-width />
                                                </template>

                                                <template v-for="ac in props.actions">
                                                    <BDropdownItem
                                                        v-if="ac.visible ?? true"
                                                        :id="ac.id"
                                                        :key="ac.id"
                                                        :disabled="ac.disabled"
                                                        :size="ac.size || 'sm'"
                                                        :variant="ac.variant || 'link'"
                                                        :to="ac.to"
                                                        :title="ac.title"
                                                        :href="ac.href"
                                                        :target="ac.externalLink ? '_blank' : undefined"
                                                        @click.stop="
                                                            ac.handler &&
                                                            ac.handler(item, getGlobalIndex(paginatedIndex))
                                                        ">
                                                        <FontAwesomeIcon v-if="ac.icon" :icon="ac.icon" fixed-width />
                                                        {{ ac.label }}
                                                    </BDropdownItem>
                                                </template>
                                            </BDropdown>
                                        </slot>
                                    </td>
                                </tr>
                            </template>

                            <!-- Row details expansion -->
                            <tr
                                v-if="isRowExpanded(getGlobalIndex(paginatedIndex))"
                                :key="`details-${getGlobalIndex(paginatedIndex)}`"
                                class="g-table-details-row">
                                <td :colspan="props.fields.length + (selectable ? 1 : 0) + (props.actions ? 1 : 0)">
                                    <slot
                                        name="row-details"
                                        :item="item"
                                        :index="getGlobalIndex(paginatedIndex)"
                                        :toggle-details="() => toggleRowDetails(getGlobalIndex(paginatedIndex))" />
                                </td>
                            </tr>
                        </template>
                    </tbody>
                </table>

                <!-- Load more loading indicator -->
                <div v-if="loadMoreLoading && localItems.length > 0" class="g-table-load-more py-3 text-center">
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
.g-table-container {
    container-type: inline-size;
    container-name: g-table;

    .g-table-sticky-header {
        overflow-y: auto;
        max-height: v-bind(stickyHeaderMaxHeight);
    }

    @mixin g-table-stacked-layout {
        display: block;
        overflow-x: visible;

        thead {
            display: block;
            position: sticky;
            top: 0;
            background-color: $body-bg;
            z-index: 9;

            tr {
                display: block;
                border: none;
            }

            th {
                display: none;

                &.g-table-select-column {
                    display: flex;
                    align-items: center;
                    gap: 0.5rem;
                    width: 100%;
                    padding: 0.75rem;
                    border-bottom: 2px solid $brand-secondary;

                    &::after {
                        content: "Select all";
                        font-weight: 500;
                        color: inherit;
                    }
                }
            }
        }

        tbody,
        tr {
            display: block;
            border: none;
        }

        tr {
            margin-bottom: 1rem;
            border: 1px solid $brand-secondary;
            border-radius: 0.25rem;
        }

        td {
            display: block;
            width: 100%;
            text-align: right;
            padding: 0.5rem;
            border-bottom: 1px solid $brand-secondary;

            &[data-label]::before {
                content: attr(data-label);
                float: left;
                font-weight: 600;
                text-align: left;
            }
        }

        .g-table-select-column,
        .g-table-actions-column {
            display: flex;
            width: 100%;
            justify-content: center;
            text-align: center;

            &::before {
                content: none;
            }
        }
    }

    .g-table {
        &.g-table-fixed {
            table-layout: fixed;
            width: 100%;
        }

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

            .g-table-sort-icon {
                color: $brand-secondary;
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

                box-shadow: inset 0 -1px 0 0 rgba($brand-primary, 0.2);

                &.g-table-row-selected {
                    background-color: $brand-light;
                }

                &.g-table-details-row {
                    background-color: lighten($brand-light, 0.3);
                }
            }

            td {
                padding: 0.75rem;
                vertical-align: middle;
            }
        }

        &.g-table-compact {
            thead th,
            tbody td {
                padding: 0.3rem;
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

        &.g-table-stacked {
            @include g-table-stacked-layout;
        }

        &.g-table-stacked-sm {
            @container g-table (max-width: #{$breakpoint-sm}) {
                @include g-table-stacked-layout;
            }
        }

        &.g-table-stacked-md {
            @container g-table (max-width: #{$breakpoint-md}) {
                @include g-table-stacked-layout;
            }
        }

        &.g-table-stacked-lg {
            @container g-table (max-width: #{$breakpoint-lg}) {
                @include g-table-stacked-layout;
            }
        }

        &.g-table-stacked-xl {
            @container g-table (max-width: #{$breakpoint-xl}) {
                @include g-table-stacked-layout;
            }
        }

        &.caption-top {
            caption {
                caption-side: top;
            }
        }
    }

    .g-table-load-more {
        border-top: 1px solid $brand-secondary;
    }
}
</style>

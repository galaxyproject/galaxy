<script setup lang="ts" generic="T extends Record<string, any>">
import { faEllipsisV, faSort, faSortDown, faSortUp } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BDropdown, BDropdownItem, BFormCheckbox, BOverlay } from "bootstrap-vue";
import { computed, ref } from "vue";

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
     * Whether rows are clickable
     * @default false
     */
    clickableRows?: boolean;

    /**
     * Additional CSS classes for the table container
     * @default ""
     */
    containerClass?: string | string[];

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
     * Whether to show hover effect on rows
     * @default true
     */
    hover?: boolean;

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
     * Row status icon getter - renders icon inline with first data column
     * Return undefined to skip icon for a row
     * @default undefined
     */
    statusIcon?: (item: T, index: number) => RowIcon | undefined;

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
    clickableRows: false,
    containerClass: "",
    emptyState: () => ({ message: "No data available" }),
    fields: () => [],
    hover: true,
    items: () => [],
    loading: false,
    loadingMessage: "Loading...",
    loadMoreLoading: false,
    loadMoreMessage: "Loading more...",
    overlayLoading: false,
    selectable: false,
    selectedItems: () => [],
    showSelectAll: false,
    sortBy: "",
    sortDesc: false,
    striped: true,
    statusIcon: undefined,
    tableClass: "",
});

/**
 * Events emitted by the GTable component
 */
const emit = defineEmits<{
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

const localItems = computed(() => props.items || []);
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

    emit("row-click", { item, index, event });
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
</script>

<template>
    <div :id="`g-table-container-${props.id}`" class="w-100" :class="containerClass">
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
                                :style="field.width ? { width: field.width } : undefined"
                                @click="onHeaderClick(field)">
                                <div class="d-flex align-items-center">
                                    <div class="flex-grow-1" :class="getTextAlignmentClass(field.align)">
                                        <slot :name="`head(${field.key})`" :field="field">
                                            {{ field.label || field.key }}
                                        </slot>
                                    </div>
                                    <FontAwesomeIcon
                                        v-if="field.sortable && getSortIcon(field)"
                                        :icon="getSortIcon(field)"
                                        :class="{ 'text-muted': sortBy !== field.key }"
                                        class="ml-1 flex-shrink-0" />
                                </div>
                            </th>

                            <th v-if="props.actions" class="g-table-actions-column">
                                <slot name="head-actions">Actions</slot>
                            </th>
                        </tr>
                    </thead>

                    <tbody v-if="localItems.length > 0">
                        <tr
                            v-for="(item, index) in localItems"
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
                                    title="Select for bulk actions"
                                    @click.stop
                                    @change="onRowSelect(item, index)" />
                            </td>

                            <!-- Data columns -->
                            <td
                                v-for="(field, fieldIndex) in props.fields"
                                :id="getCellId(props.id, field.key, index)"
                                :key="field.key"
                                :class="[
                                    field.cellClass,
                                    field.class,
                                    getAlignmentClass(field.align),
                                    { 'hide-on-small': field.hideOnSmall },
                                ]">
                                <template v-if="fieldIndex === 0 && getStatusIcon(item, index)">
                                    <FontAwesomeIcon
                                        v-if="getStatusIcon(item, index)"
                                        v-b-tooltip.hover.noninteractive
                                        v-bind="getIconProps(item, index)"
                                        fixed-width />
                                </template>

                                <slot :name="`cell(${field.key})`" :value="item[field.key]" :item="item" :index="index">
                                    <span>{{ getCellValue(item, field) }}</span>
                                </slot>
                            </td>

                            <!-- Actions column -->
                            <td v-if="props.actions" class="g-table-actions-column">
                                <slot name="actions" :item="item" :index="index">
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
                                                @click.stop="ac.handler && ac.handler(item, index)">
                                                <FontAwesomeIcon v-if="ac.icon" :icon="ac.icon" fixed-width />
                                                {{ ac.label }}
                                            </BDropdownItem>
                                        </template>
                                    </BDropdown>
                                </slot>
                            </td>
                        </tr>
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

            box-shadow: inset 0 -1px 0 0 rgba($brand-primary, 0.2);

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

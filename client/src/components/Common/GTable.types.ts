import type { IconDefinition } from "@fortawesome/free-solid-svg-icons";

import type { BootstrapVariant } from "@/components/Common";

/** Bootstrap component sizes */
export type BootstrapSize = "xs" | "sm" | "md" | "lg" | "xl";

/** Table field sorting order */
export type SortOrder = "asc" | "desc";

/** Table field alignment options */
export type FieldAlignment = "left" | "center" | "right";

/** Table field definition */
export interface TableField {
    /** Unique key for the field (matches data property name) */
    key: string;
    /** Display label for the column header */
    label?: string;
    /** Whether the column is sortable */
    sortable?: boolean;
    /** Custom CSS classes for the column */
    class?: string;
    /** Custom CSS classes for the header cell */
    headerClass?: string;
    /** Custom CSS classes for data cells */
    cellClass?: string;
    /** Column alignment */
    align?: FieldAlignment;
    /** Width of the column (CSS value) */
    width?: string;
    /** Whether to hide the column on small screens */
    hideOnSmall?: boolean;
    /** Custom formatter function for cell values */
    formatter?: (value: any, key: string, item: any) => string;
    /** Whether to render as HTML (use with caution) */
    html?: boolean;
}

/** Sort change event payload */
export interface SortChangeEvent {
    /** The field key being sorted */
    sortBy: string;
    /** Whether sorting in descending order */
    sortDesc: boolean;
}

/** Row click event payload */
export interface RowClickEvent<T = any> {
    /** The row item data */
    item: T;
    /** The row index */
    index: number;
    /** The original mouse/keyboard event */
    event: MouseEvent | KeyboardEvent;
}

/** Row selection event payload */
export interface RowSelectEvent<T = any> {
    /** The selected row item */
    item: T;
    /** The row index */
    index: number;
    /** Whether the row is now selected */
    selected: boolean;
}

/** Table action button configuration */
export interface TableAction {
    /** Unique identifier for the action */
    id: string;
    /** Display label for the action */
    label: string;
    /** Tooltip text */
    title: string;
    /** FontAwesome icon */
    icon?: IconDefinition;
    /** Bootstrap variant */
    variant?: BootstrapVariant;
    /** Whether the action is disabled */
    disabled?: boolean;
    /** Whether the action is visible */
    visible?: boolean;
    /** Bootstrap component size */
    size?: BootstrapSize;
    /** Vue Router route to navigate to */
    to?: string;
    /** Hyperlink reference */
    href?: string;
    /** Link target attribute */
    target?: string;
    /** Whether link opens in new tab/window */
    externalLink?: boolean;
    /** Click handler function */
    handler?: (item: any, index: number) => void;
}

/** Empty state configuration */
export interface TableEmptyState {
    /** Message to display when no data */
    message: string;
    /** Optional icon to display */
    icon?: IconDefinition;
    /** Bootstrap variant for styling */
    variant?: BootstrapVariant;
}

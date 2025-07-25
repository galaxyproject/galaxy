import type { RawLocation } from "vue-router";

// TODO: Not sure if this is the best place for this type
export type ColorVariant = "primary" | "secondary" | "success" | "danger" | "warning" | "info" | "light" | "dark";

/**
 * Represents a breadcrumb item in the BreadcrumbHeading component.
 * Each item can have a title, an optional URL to navigate to, and optional additional text
 * displayed alongside the item.
 */
export interface BreadcrumbItem {
    /** The display text for the breadcrumb item */
    title: string;
    /** Optional The URL or route to navigate to when the breadcrumb item is clicked.
     * the item will not be clickable if this is not provided or the current route matches this location.
     */
    to?: RawLocation;
    /**
     * Optional additional text displayed above the item.
     */
    superText?: string;
}

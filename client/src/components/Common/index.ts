import type { IconDefinition } from "@fortawesome/fontawesome-svg-core";
import type { RawLocation } from "vue-router";

/**
 * Basic color variants for components that only support
 * color-based styling like alerts, badges, and backgrounds (no outline variants).
 */
export type ColorVariant = "primary" | "secondary" | "success" | "danger" | "warning" | "info" | "light" | "dark";

/**
 * Bootstrap Vue variants for styling components.
 * Includes basic color variants plus outline variants for buttons and modals.
 */
export type BootstrapVariant =
    | ColorVariant
    | "link"
    | "outline-primary"
    | "outline-secondary"
    | "outline-success"
    | "outline-danger"
    | "outline-warning"
    | "outline-info"
    | "outline-light"
    | "outline-link"
    | "outline-dark";

/**
 * Represents a breadcrumb item in the BreadcrumbHeading component.
 * Each item can have a title, an optional URL to navigate to, and optional additional text
 * displayed alongside the item.
 */
export interface BreadcrumbItem {
    /**
     * The label of the breadcrumb item.
     */
    title: string;

    /**
     * Optional The URL or route to navigate to when the breadcrumb item is clicked.
     * the item will not be clickable if this is not provided or the current route matches this location.
     */
    to?: RawLocation;

    /**
     * Optional additional text displayed above the item.
     */
    superText?: string;

    /**
     * Optional icon to display alongside the breadcrumb item.
     */
    icon?: IconDefinition;
}

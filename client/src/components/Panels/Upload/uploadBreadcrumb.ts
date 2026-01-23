import type { BreadcrumbItem } from "@/components/Common";

/**
 * Base breadcrumb for Upload-related views.
 * Centralized to ensure consistent labeling (e.g. Beta status)
 * across all upload methods and pages.
 */
export function getUploadRootBreadcrumb(to?: string): BreadcrumbItem {
    return {
        title: "Import Data",
        superText: "Beta",
        ...(to ? { to } : {}),
    };
}

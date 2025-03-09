// TODO: Not sure if this is the best place for this type
export type ColorVariant = "primary" | "secondary" | "success" | "danger" | "warning" | "info" | "light" | "dark";

export interface BreadcrumbItem {
    title: string;
    to?: string;
    superText?: string;
}

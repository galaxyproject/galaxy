import type { ComponentColor, ComponentSize } from "./componentVariants";

/** Map a bootstrap-vue BButton variant string to GButton color/outline/transparent attributes. */
export function variantToColor(variant: string | null | undefined): {
    color?: ComponentColor;
    outline?: boolean;
    transparent?: boolean;
} {
    if (!variant) {
        return {};
    }
    const isOutline = variant.startsWith("outline-");
    const base = isOutline ? variant.slice("outline-".length) : variant;
    switch (base) {
        case "primary":
        case "info":
            return { color: "blue", outline: isOutline };
        case "danger":
        case "error":
            return { color: "red", outline: isOutline };
        case "success":
            return { color: "green", outline: isOutline };
        case "warning":
            return { color: "yellow", outline: isOutline };
        case "secondary":
        case "default":
            return { outline: isOutline };
        case "link":
            return { transparent: true };
        case "disabled":
            return {};
        case "dark":
        case "light":
        case "white":
            return { transparent: true };
        default:
            return {};
    }
}

/** Map a bootstrap-vue BButton size string to GButton size. */
export function sizeToGSize(size: string | null | undefined): ComponentSize | undefined {
    if (!size) {
        return undefined;
    }
    if (size === "sm" || size === "xs") {
        return "small";
    }
    if (size === "lg") {
        return "large";
    }
    if (size === "md") {
        return undefined;
    }
    return undefined;
}

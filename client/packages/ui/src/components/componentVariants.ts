export type ComponentColor = "grey" | "blue" | "green" | "yellow" | "orange" | "red";
export type ComponentSize = "small" | "medium" | "large";

/**
 * Basic color variants for components that only support
 * color-based styling like alerts and backgrounds (no outline variants).
 */
export type ColorVariant = "primary" | "secondary" | "success" | "danger" | "warning" | "info" | "light" | "dark";

/** Badge variants: a solid color, or the same color as an outline on the page background. */
export type BadgeVariant = ColorVariant | `outline-${ColorVariant}`;

export type ComponentSizeClassList = {
    [_key in `g-${ComponentSize}`]?: true;
};

export type ComponentColorClassList = {
    [_key in `g-${ComponentColor}`]?: true;
};

export type ComponentVariantClassList = ComponentSizeClassList & ComponentColorClassList;

export function prefix<T extends string>(key: T): `g-${T}` {
    return `g-${key}`;
}

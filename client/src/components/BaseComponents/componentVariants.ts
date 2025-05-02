export type ComponentColor = "grey" | "blue" | "green" | "yellow" | "orange" | "red";
export type ComponentSize = "small" | "medium" | "large";

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

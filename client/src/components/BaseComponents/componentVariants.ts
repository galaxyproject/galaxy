export type ComponentColor = "grey" | "blue" | "green" | "yellow" | "orange" | "red";
export type ComponentSize = "small" | "medium" | "large";

export type ComponentVariantClassList = {
    [_key in `g-${ComponentSize}`]?: true;
} & {
    [_key in `g-${ComponentColor}`]?: true;
};

export function prefix<T extends string>(key: T): `g-${T}` {
    return `g-${key}`;
}

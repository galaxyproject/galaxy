type BorderVariant = "primary" | "default";

export function borderVariant(isPrimary: boolean): BorderVariant {
    return isPrimary ? "primary" : "default";
}

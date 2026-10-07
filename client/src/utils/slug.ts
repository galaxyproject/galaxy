/** Lowercase dash-joined slug of `text`, or `fallback` when no usable character is left */
export function slugify(text: string, fallback: string): string {
    const slug = text
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-+|-+$/g, "");
    return slug || fallback;
}

/**
 * Turns free text into a URL slug: lowercase, every run of other characters
 * turned into a single dash, no dash at either end.
 *
 * @param text free text, e.g. a title
 * @param fallback returned when the text has no usable character at all
 */
export function slugify(text: string, fallback: string): string {
    const slug = text
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-+|-+$/g, "");
    return slug || fallback;
}

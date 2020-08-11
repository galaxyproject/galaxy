/*
 * Utilities for working with upload data structures.
 */

export function findExtension(extensions, id) {
    return extensions.find((extension) => extension.id == id);
}

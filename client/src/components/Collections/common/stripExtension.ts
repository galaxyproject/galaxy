import { computed } from "vue";

import type { HistoryItemSummary } from "@/api";

export function stripExtension(filename_: string): string {
    let filename = filename_;
    let strippedSecondaryExtension = false;

    const secondaryExtensions = [".gz", ".bz2", ".tgz", ".crai", ".bai"];
    const hasSecondaryExtension = (name: string): string | null => {
        for (const ext of secondaryExtensions) {
            if (name.endsWith(ext)) {
                return ext;
            }
        }
        return null;
    };

    // Remove multi-part extensions
    const secondaryExt = hasSecondaryExtension(filename);
    if (secondaryExt) {
        strippedSecondaryExtension = true;
        // Strip secondary extension first
        filename = filename.slice(0, -secondaryExt.length);
    }

    // Remove single extensions (anything after the last dot)
    const lastDotIndex = filename.lastIndexOf(".");
    const maxLengthOfExtension = strippedSecondaryExtension ? 7 : 10; // if we've already stripped some extension - be more conservative
    if (lastDotIndex !== -1) {
        const extensionLength = filename.length - lastDotIndex;
        if (extensionLength < maxLengthOfExtension) {
            filename = filename.slice(0, lastDotIndex);
        }
    }

    return filename;
}

interface HasInitialItemsProp {
    initialElements: HistoryItemSummary[];
}

interface HasNameAndIdentifier {
    id: string;
    identifier: string | null;
}

export function useUpdateIdentifiersForRemoveExtensions(props: HasInitialItemsProp) {
    const initialElementsById = computed(() => {
        const byId = {} as Record<string, HistoryItemSummary>;
        for (const initialElement of props.initialElements) {
            byId[initialElement.id] = initialElement;
        }
        return byId;
    });

    function updateIdentifierIfUnchanged(
        element: HistoryItemSummary | HasNameAndIdentifier,
        updatedRemoveExtensions: boolean
    ) {
        const byId = initialElementsById.value;
        const originalName = byId[element.id]?.name;

        if (updatedRemoveExtensions) {
            // switching from not remove extensions to remove extensions
            const originalName = byId[element.id]?.name;
            if ("name" in element) {
                if (originalName && element.name == originalName) {
                    element.name = stripExtension(originalName);
                }
            } else {
                if (originalName && element.identifier == originalName) {
                    element.identifier = stripExtension(originalName);
                }
            }
        } else {
            if (originalName) {
                const strippedOriginalName = stripExtension(originalName);
                if ("name" in element) {
                    if (strippedOriginalName && element.name == strippedOriginalName) {
                        element.name = originalName;
                    }
                } else {
                    if (strippedOriginalName && element.identifier == strippedOriginalName) {
                        element.identifier = originalName;
                    }
                }
            }
        }
    }

    return { updateIdentifierIfUnchanged, initialElementsById };
}

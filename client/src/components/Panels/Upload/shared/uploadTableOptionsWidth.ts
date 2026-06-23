import type { UploadOptionVisibility } from "./uploadOptionVisibility";

const toggleWidths = {
    spaceToTab: 84,
    posix: 54,
    deferred: 82,
    autoDecompress: 102,
};

/**
 * Returns a table column width that matches visible upload settings toggles.
 */
export function getUploadSettingsColumnWidth(visibility: UploadOptionVisibility): string {
    const visibleCount = Object.values(visibility).filter(Boolean).length;

    let width = 8 + Math.max(0, visibleCount - 1) * 8;

    if (visibility.spaceToTab) {
        width += toggleWidths.spaceToTab;
    }
    if (visibility.posix) {
        width += toggleWidths.posix;
    }
    if (visibility.deferred) {
        width += toggleWidths.deferred;
    }
    if (visibility.autoDecompress) {
        width += toggleWidths.autoDecompress;
    }

    return `${Math.max(140, width)}px`;
}

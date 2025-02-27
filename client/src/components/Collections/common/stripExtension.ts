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

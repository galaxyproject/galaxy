/** Accepted workflow file extensions */
export const WORKFLOW_FILE_EXTENSIONS = [".ga", ".gxwf.yml", ".gxwf.yaml", ".yml", ".yaml"] as const;

/** Human-readable list of accepted formats for file inputs */
export const WORKFLOW_FILE_ACCEPT = ".ga, .yml, .yaml";

/**
 * Check if a filename has a valid workflow file extension.
 * Supports .ga (Galaxy Archive), .yml/.yaml (Galaxy Workflow Format), and .gxwf.yml/.gxwf.yaml
 */
export function hasWorkflowFileExtension(fileName: string): boolean {
    const lowerName = fileName.toLowerCase();
    return WORKFLOW_FILE_EXTENSIONS.some((ext) => lowerName.endsWith(ext));
}

/**
 * Validate a workflow file by checking its extension and optionally its content.
 *
 * For .ga files (JSON format), checks for `"a_galaxy_workflow": "true"`.
 * For .yml/.yaml files (YAML format), checks for `class: GalaxyWorkflow` or `class: GalaxyWorkflow`.
 *
 * Content validation reads only the first 1KB of the file for efficiency.
 */
export async function validateWorkflowFile(
    file: File,
    options: { checkContent?: boolean } = {},
): Promise<{ valid: boolean; error?: string }> {
    if (!hasWorkflowFileExtension(file.name)) {
        return { valid: false, error: `Invalid file type. Accepted formats: ${WORKFLOW_FILE_ACCEPT}` };
    }

    if (options.checkContent) {
        const lowerName = file.name.toLowerCase();

        if (lowerName.endsWith(".ga")) {
            const hasMarker = await readFileMarker(file, '"a_galaxy_workflow"');
            if (!hasMarker) {
                return {
                    valid: false,
                    error: "File does not appear to be a Galaxy workflow (.ga). Missing workflow marker.",
                };
            }
        } else if (lowerName.endsWith(".yml") || lowerName.endsWith(".yaml")) {
            const hasMarker = await readFileMarker(file, "class:");
            if (!hasMarker) {
                return {
                    valid: false,
                    error: "File does not appear to be a Galaxy workflow (.yml/.yaml). Missing 'class:' marker.",
                };
            }
        }
    }

    return { valid: true };
}

/**
 * Read the first 1KB of a file and check if it contains the given marker string.
 * This is efficient and avoids loading the entire file into memory.
 */
async function readFileMarker(file: File, marker: string): Promise<boolean> {
    try {
        const slice = file.slice(0, 1024);
        const text = await slice.text();
        return text.includes(marker);
    } catch {
        return false;
    }
}

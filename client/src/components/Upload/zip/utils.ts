export function isZipFile(file?: File | null): string {
    if (!file) {
        return "No file selected";
    }

    if (file.type !== "application/zip") {
        return "Invalid file type. Please select a ZIP file.";
    }

    return "";
}

export const GALAXY_EXPORT_METADATA_FILES = [
    "collections_attrs.txt",
    "datasets_attrs.txt",
    "datasets_attrs.txt.provenance",
    "export_attrs.txt",
    "implicit_collection_jobs_attrs.txt",
    "implicit_dataset_conversions.txt",
    "invocation_attrs.txt",
    "jobs_attrs.txt",
    "libraries_attrs.txt",
    "library_folders_attrs.txt",
];

// TODO: Move RO-Crate specifics to another file

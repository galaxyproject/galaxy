/** Batch mode variations */
export const Batch = { DISABLED: "disabled", ENABLED: "enabled", LINKED: "linked" };

interface VariantInterface {
    batch: string;
    icon: string;
    library?: boolean;
    multiple: boolean;
    src: string;
    tooltip: string;
}

/** List of available content selectors options */
export const Variants: Record<string, Array<VariantInterface>> = {
    data: [
        {
            src: "hda",
            icon: "fa-file-o",
            tooltip: "Single dataset",
            library: true,
            multiple: false,
            batch: Batch.DISABLED,
        },
        {
            src: "hda",
            icon: "fa-files-o",
            tooltip: "Multiple datasets",
            multiple: true,
            batch: Batch.LINKED,
        },
        {
            src: "hdca",
            icon: "fa-folder-o",
            tooltip: "Dataset collection",
            multiple: false,
            batch: Batch.LINKED,
        },
    ],
    data_multiple: [
        {
            src: "hda",
            icon: "fa-files-o",
            tooltip: "Multiple datasets",
            multiple: true,
            batch: Batch.DISABLED,
        },
        {
            src: "hdca",
            icon: "fa-folder-o",
            tooltip: "Dataset collections",
            multiple: true,
            batch: Batch.DISABLED,
        },
    ],
    data_collection: [
        {
            src: "hdca",
            icon: "fa-folder-o",
            tooltip: "Dataset collection",
            multiple: false,
            batch: Batch.DISABLED,
        },
    ],
    workflow_data: [
        {
            src: "hda",
            icon: "fa-file-o",
            tooltip: "Single dataset",
            multiple: false,
            batch: Batch.DISABLED,
        },
    ],
    workflow_data_multiple: [
        {
            src: "hda",
            icon: "fa-files-o",
            tooltip: "Multiple datasets",
            multiple: true,
            batch: Batch.DISABLED,
        },
    ],
    workflow_data_collection: [
        {
            src: "hdca",
            icon: "fa-folder-o",
            tooltip: "Dataset collection",
            multiple: false,
            batch: Batch.DISABLED,
        },
    ],
    module_data: [
        {
            src: "hda",
            icon: "fa-file-o",
            tooltip: "Single dataset",
            multiple: false,
            batch: Batch.DISABLED,
        },
        {
            src: "hda",
            icon: "fa-files-o",
            tooltip: "Multiple datasets",
            multiple: true,
            batch: Batch.ENABLED,
        },
    ],
    module_data_collection: [
        {
            src: "hdca",
            icon: "fa-folder-o",
            tooltip: "Dataset collection",
            multiple: false,
            batch: Batch.DISABLED,
        },
        {
            src: "hdca",
            icon: "fa-folder",
            tooltip: "Multiple collections",
            multiple: true,
            batch: Batch.ENABLED,
        },
    ],
};

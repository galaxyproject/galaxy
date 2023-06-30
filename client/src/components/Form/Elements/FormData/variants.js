/** Batch mode variations */
export const Batch = { DISABLED: "disabled", ENABLED: "enabled", LINKED: "linked" };

/** List of available content selectors options */
export const Configurations = {
    data: [
        {
            src: "hda",
            icon: "fa-file-o",
            tooltip: _l("Single dataset"),
            library: true,
            multiple: false,
            batch: Batch.DISABLED,
        },
        {
            src: "hda",
            icon: "fa-files-o",
            tooltip: _l("Multiple datasets"),
            multiple: true,
            batch: Batch.LINKED,
        },
        {
            src: "hdca",
            icon: "fa-folder-o",
            tooltip: _l("Dataset collection"),
            multiple: false,
            batch: Batch.LINKED,
        },
    ],
    data_multiple: [
        {
            src: "hda",
            icon: "fa-files-o",
            tooltip: _l("Multiple datasets"),
            multiple: true,
            batch: Batch.DISABLED,
        },
        {
            src: "hdca",
            icon: "fa-folder-o",
            tooltip: _l("Dataset collections"),
            multiple: true,
            batch: Batch.DISABLED,
        },
    ],
    data_collection: [
        {
            src: "hdca",
            icon: "fa-folder-o",
            tooltip: _l("Dataset collection"),
            multiple: false,
            batch: Batch.DISABLED,
        },
    ],
    workflow_data: [
        {
            src: "hda",
            icon: "fa-file-o",
            tooltip: _l("Single dataset"),
            multiple: false,
            batch: Batch.DISABLED,
        },
    ],
    workflow_data_multiple: [
        {
            src: "hda",
            icon: "fa-files-o",
            tooltip: _l("Multiple datasets"),
            multiple: true,
            batch: Batch.DISABLED,
        },
    ],
    workflow_data_collection: [
        {
            src: "hdca",
            icon: "fa-folder-o",
            tooltip: _l("Dataset collection"),
            multiple: false,
            batch: Batch.DISABLED,
        },
    ],
    module_data: [
        {
            src: "hda",
            icon: "fa-file-o",
            tooltip: _l("Single dataset"),
            multiple: false,
            batch: Batch.DISABLED,
        },
        {
            src: "hda",
            icon: "fa-files-o",
            tooltip: _l("Multiple datasets"),
            multiple: true,
            batch: Batch.ENABLED,
        },
    ],
    module_data_collection: [
        {
            src: "hdca",
            icon: "fa-folder-o",
            tooltip: _l("Dataset collection"),
            multiple: false,
            batch: Batch.DISABLED,
        },
        {
            src: "hdca",
            icon: "fa-folder",
            tooltip: _l("Multiple collections"),
            multiple: true,
            batch: Batch.ENABLED,
        },
    ],
};

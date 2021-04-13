import UploadUtils from "mvc/upload/upload-utils";

export const commonProps = {
    uploadPath: {
        type: String,
        required: true,
    },
    chunkUploadSize: {
        type: Number,
        required: true,
    },
    fileSourcesConfigured: {
        type: Boolean,
        required: true,
    },
    ftpUploadSite: {
        type: String,
        default: "",
    },
    defaultGenome: {
        type: String,
        default: UploadUtils.DEFAULT_GENOME,
    },
    defaultExtension: {
        type: String,
        default: UploadUtils.DEFAULT_EXTENSION,
    },
    datatypesDisableAuto: {
        type: Boolean,
        default: false,
    },
    formats: {
        type: Array,
        default: null,
    },
    multiple: {
        // Restrict the forms to a single dataset upload if false
        type: Boolean,
        default: true,
    },
    hasCallback: {
        // Return uploads when done if supplied.
        type: Boolean,
        default: false,
    },
    selectable: {
        type: Boolean,
        required: false,
        default: false,
    },
    auto: {
        type: Object,
        default: function () {
            return UploadUtils.AUTO_EXTENSION;
        },
    },
};

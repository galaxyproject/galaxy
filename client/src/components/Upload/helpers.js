import UploadUtils from "mvc/upload/upload-utils";
export const defaultNewFileName = "New File";

const URI_PREFIXES = ["http", "https", "ftp", "file", "gxfiles", "gximport", "gxuserimport", "gxftp"];
function itemIsUrl(item) {
    return URI_PREFIXES.some((prefix) => item.get("url_paste").startsWith(prefix));
}

export function uploadModelsToPayload(items, history_id, composite = false) {
    const files = [];
    const elements = items
        .map((item) => {
            if (item.get("optional")) {
                return null;
            }
            let src;
            let pasteContent = null;
            let fileName = item.get("file_name");
            if (fileName === defaultNewFileName) {
                fileName = null;
            }
            const url = (item.get("file_uri") || item.get("file_path") || item.get("url_paste")).trim();
            const elem = {
                dbkey: item.get("genome", "?"),
                ext: item.get("extension", "auto"),
                space_to_tab: item.get("space_to_tab"),
                to_posix_lines: item.get("to_posix_lines"),
                deferred: item.get("deferred"),
            };
            switch (item.get("file_mode")) {
                case "new":
                    if (itemIsUrl(item)) {
                        src = "url";
                        /* Could be multiple URLs pasted in.
                          TODO: eliminate backbone models,
                          then suggest to split multiple URLs
                          across multiple uploads directly in upload modal,
                          instead of this intransparent magic. */
                        return url.split("\n").map((splitUrl) => {
                            return {
                                src: src,
                                url: splitUrl,
                                name: fileName,
                                ...elem,
                            };
                        });
                    } else {
                        pasteContent = item.get("url_paste");
                        src = "pasted";
                    }
                    break;
                case "ftp":
                    if (url.indexOf("://") >= 0) {
                        src = "url";
                    }
                    break;
                case "local":
                    src = "files";
                    files.push(item.get("file_data"));
                    break;
                default:
                    console.error("Unknown file_mode", item);
            }
            if (src == "pasted") {
                return {
                    src: src,
                    paste_content: pasteContent,
                    name: fileName,
                    ...elem,
                };
            } else if (src == "url") {
                return {
                    src: src,
                    name: fileName,
                    url: url,
                    ...elem,
                };
            } else {
                return {
                    src: src,
                    name: fileName,
                    ...elem,
                };
            }
        })
        .filter((item) => item)
        .flat();
    const target = {
        destination: { type: "hdas" },
        elements: elements,
    };
    if (composite) {
        const compositeItems = [
            {
                src: "composite",
                ext: elements[0].ext,
                composite: {
                    items: target.elements,
                },
            },
        ];
        delete target["elements"];
        target["items"] = compositeItems;
    }
    return {
        history_id: history_id,
        targets: [target],
        auto_decompress: true,
        files: files,
    };
}

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

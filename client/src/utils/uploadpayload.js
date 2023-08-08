export const DEFAULT_FILE_NAME = "New File";
export const URI_PREFIXES = [
    "http://",
    "https://",
    "ftp://",
    "file://",
    "gxfiles://",
    "gximport://",
    "gxuserimport://",
    "gxftp://",
    "drs://",
];

export function uploadPayload(items, history_id, composite = false) {
    const files = [];
    const elements = items
        .map((item) => {
            if (item.optional) {
                return null;
            }
            let src;
            let pasteContent = null;
            let fileName = item.fileName;
            if (fileName === DEFAULT_FILE_NAME) {
                fileName = null;
            }
            const url = (item.fileUri || item.filePath || item.fileContent).trim();
            const elem = {
                dbkey: item.dbKey ?? "?",
                ext: item.extension ?? "auto",
                space_to_tab: item.spaceToTab,
                to_posix_lines: item.toPosixLines,
                deferred: item.deferred,
            };
            const isUrl = URI_PREFIXES.some((prefix) => item.fileContent.startsWith(prefix));
            switch (item.fileMode) {
                case "new":
                    if (isUrl) {
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
                        pasteContent = item.fileContent;
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
                    files.push(item.fileData);
                    break;
                default:
                    console.error("Unknown fileMode", item);
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

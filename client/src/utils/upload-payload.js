export const DEFAULT_FILE_NAME = "New File";
export const URI_PREFIXES = [
    "http://",
    "https://",
    "ftp://",
    "file://",
    "gxfiles://",
    "gximport://",
    "gxuserimport://",
    "gxuserfiles://",
    "gxftp://",
    "drs://",
    "invenio://",
    "zenodo://",
];

export function isUrl(content) {
    return URI_PREFIXES.some((prefix) => content.startsWith(prefix));
}

export function isGalaxyFile(content) {
    if (content === undefined || content === null) {
        return false;
    }
    const galaxyRegexPattern = /Galaxy\d+-\[(.*?)\](\..+)/;
    const match = content.match(galaxyRegexPattern);
    if (match) {
        console.log(`Uploaded file has previous Galaxy annotated filename: "${content}"`);
        return true;
    } else {
        return false;
    }
}

export function uploadPayload(items, historyId, composite = false) {
    const files = [];
    const elements = items
        .map((item) => {
            if (!item.optional || item.fileSize > 0) {
                // avoid submitting default file name, server will set file name
                let fileName = item.fileName;
                if (fileName === DEFAULT_FILE_NAME) {
                    fileName = null;
                }
                if (isGalaxyFile(item.fileName)) {
                    const modifiedFileName = item.fileName.replace(/Galaxy\d+-\[(.*?)\](\..+)/, "$1");
                    const keepModifiedName = confirm(
                        `This looks like a previous Galaxy file. We have renamed it.\n\nOriginal Name: ${item.fileName}\nModified Name: ${modifiedFileName}\n\n Do you want to keep the modified name?`
                    );
                    if (keepModifiedName) {
                        item.fileName = modifiedFileName;
                        fileName = modifiedFileName;
                    }
                }
                // consolidate exclusive file content attributes
                const urlContent = (item.fileUri || item.filePath || item.fileContent || "").trim();
                const hasFileData = item.fileData && item.fileData.size > 0;
                if (urlContent.length === 0 && !hasFileData) {
                    throw new Error("Content not available.");
                }
                // collect common element attributes
                const elem = {
                    dbkey: item.dbKey ?? "?",
                    ext: item.extension ?? "auto",
                    name: fileName,
                    space_to_tab: item.spaceToTab,
                    to_posix_lines: item.toPosixLines,
                    deferred: item.deferred,
                };
                // match file mode
                switch (item.fileMode) {
                    case "new":
                        if (isUrl(urlContent)) {
                            /* Could be multiple URLs pasted in.
                            TODO: suggesting to split multiple URLs
                            across multiple uploads directly in upload modal,
                            instead of this intransparent magic. */
                            return urlContent.split("\n").map((urlSplit) => {
                                const urlTrim = urlSplit.trim();
                                if (isUrl(urlTrim)) {
                                    return {
                                        src: "url",
                                        url: urlTrim,
                                        ...elem,
                                    };
                                } else {
                                    throw new Error(`Invalid url: ${urlTrim}`);
                                }
                            });
                        } else {
                            return {
                                src: "pasted",
                                paste_content: item.fileContent,
                                ...elem,
                            };
                        }
                    case "url":
                        if (isUrl(urlContent)) {
                            return {
                                src: "url",
                                url: urlContent,
                                ...elem,
                            };
                        } else {
                            throw new Error(`Invalid url: ${urlContent}.`);
                        }
                    case "local":
                        files.push(item.fileData);
                        return {
                            src: "files",
                            ...elem,
                        };
                    default:
                        throw new Error(`Unknown file mode: ${item.fileMode}.`);
                }
            }
        })
        .filter((item) => item)
        .flat();
    if (elements.length === 0) {
        throw new Error("No valid items provided.");
    }
    const target = {
        destination: { type: "hdas" },
        elements: elements,
    };
    if (composite) {
        const compositeItems = [
            {
                src: "composite",
                dbkey: elements[0].dbkey,
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
        history_id: historyId,
        targets: [target],
        auto_decompress: true,
        files: files,
    };
}

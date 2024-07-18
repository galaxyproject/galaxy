import { isUrl, uploadPayload } from "./upload-payload.js";

describe("uploadPayload", () => {
    test("basic validation", () => {
        expect(() => uploadPayload([], "historyId")).toThrow("No valid items provided.");
        expect(() => uploadPayload([{}], "historyId")).toThrow("Content not available.");
        expect(() => uploadPayload([{ fileContent: "fileContent" }], "historyId")).toThrow(
            "Unknown file mode: undefined."
        );
        expect(() =>
            uploadPayload(
                [
                    {
                        dbKey: "dbKey",
                        deferred: false,
                        extension: "extension",
                        fileName: "3",
                        fileContent: " http://test.me.0 \n xyz://test.me.1",
                        fileMode: "new",
                        spaceToTab: false,
                        toPosixLines: false,
                    },
                ],
                "historyId"
            )
        ).toThrow("Invalid url: xyz://test.me.1");
    });

    test("url detection", () => {
        expect(isUrl("xyz://")).toBeFalsy();
        expect(isUrl("ftp://")).toBeTruthy();
        expect(isUrl("http://")).toBeTruthy();
    });

    test("regular payload", () => {
        const p = uploadPayload(
            [
                { fileContent: " fileContent ", fileMode: "new", fileName: "1" },
                {
                    dbKey: "dbKey2",
                    deferred: true,
                    extension: "extension2",
                    fileData: { size: 1 },
                    fileMode: "local",
                    fileName: "2",
                    spaceToTab: true,
                    toPosixLines: true,
                },
                {
                    dbKey: "dbKey3",
                    deferred: false,
                    extension: "extension3",
                    fileName: "3",
                    fileContent: " http://test.me.0\nhttp://test.me.1 ",
                    fileMode: "new",
                    spaceToTab: false,
                    toPosixLines: false,
                },
                {
                    dbKey: "dbKey4",
                    deferred: false,
                    extension: "extension4",
                    fileName: "4",
                    fileUri: "http://test.me",
                    fileMode: "url",
                    spaceToTab: false,
                    toPosixLines: false,
                },
                { fileContent: " PreviousGalaxyFileContent ", fileMode: "new", fileName: "Galaxy-1[PreviousGalaxyFile].bed" },
            ],
            "historyId"
        );
        expect(p).toEqual({
            auto_decompress: true,
            files: [{ size: 1 }],
            history_id: "historyId",
            targets: [
                {
                    destination: { type: "hdas" },
                    elements: [
                        {
                            dbkey: "?",
                            deferred: undefined,
                            ext: "auto",
                            name: "1",
                            paste_content: " fileContent ",
                            space_to_tab: undefined,
                            src: "pasted",
                            to_posix_lines: undefined,
                        },
                        {
                            dbkey: "dbKey2",
                            deferred: true,
                            ext: "extension2",
                            name: "2",
                            space_to_tab: true,
                            src: "files",
                            to_posix_lines: true,
                        },
                        {
                            dbkey: "dbKey3",
                            deferred: false,
                            ext: "extension3",
                            name: "3",
                            space_to_tab: false,
                            src: "url",
                            to_posix_lines: false,
                            url: "http://test.me.0",
                        },
                        {
                            dbkey: "dbKey3",
                            deferred: false,
                            ext: "extension3",
                            name: "3",
                            space_to_tab: false,
                            src: "url",
                            to_posix_lines: false,
                            url: "http://test.me.1",
                        },
                        {
                            dbkey: "dbKey4",
                            deferred: false,
                            ext: "extension4",
                            name: "4",
                            space_to_tab: false,
                            src: "url",
                            to_posix_lines: false,
                            url: "http://test.me",
                        },
                        {
                            dbkey: "?",
                            deferred: undefined,
                            ext: "auto",
                            name: "PreviousGalaxyFile",
                            paste_content: " PreviousGalaxyFileContent ",
                            space_to_tab: undefined,
                            src: "pasted",
                            to_posix_lines: undefined,
                        },
                    ],
                },
            ],
        });
    });

    test("composite payload", () => {
        const p = uploadPayload(
            [
                { fileContent: "fileContent", fileMode: "new", fileName: "1" },
                {
                    dbKey: "dbKey",
                    deferred: true,
                    extension: "extension",
                    fileContent: "fileContent",
                    fileData: "fileData",
                    fileMode: "local",
                    fileName: "2",
                    spaceToTab: true,
                    toPosixLines: true,
                },
                { fileContent: " PreviousGalaxyFileContent ", fileMode: "new", fileName: "Galaxy-1[PreviousGalaxyFile].bed" },
            ],
            "historyId",
            true
        );
        expect(p).toEqual({
            auto_decompress: true,
            files: ["fileData"],
            history_id: "historyId",
            targets: [
                {
                    destination: { type: "hdas" },
                    items: [
                        {
                            composite: {
                                items: [
                                    {
                                        dbkey: "?",
                                        deferred: undefined,
                                        ext: "auto",
                                        name: "1",
                                        paste_content: "fileContent",
                                        space_to_tab: undefined,
                                        src: "pasted",
                                        to_posix_lines: undefined,
                                    },
                                    {
                                        dbkey: "dbKey",
                                        deferred: true,
                                        ext: "extension",
                                        name: "2",
                                        space_to_tab: true,
                                        src: "files",
                                        to_posix_lines: true,
                                    },
                                    {
                                        dbkey: "?",
                                        deferred: undefined,
                                        ext: "auto",
                                        name: "PreviousGalaxyFile",
                                        paste_content: " PreviousGalaxyFileContent ",
                                        space_to_tab: undefined,
                                        src: "pasted",
                                        to_posix_lines: undefined,
                                    },
                                ],
                            },
                            dbkey: "?",
                            ext: "auto",
                            src: "composite",
                        },
                    ],
                },
            ],
        });
    });
});

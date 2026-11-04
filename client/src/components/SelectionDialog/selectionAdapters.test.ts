import { getFakeHistorySummary } from "@tests/test-data";
import { describe, expect, it } from "vitest";

import type { HDASummary } from "@/api";
import type { BrowsableFilesSourcePlugin, RemoteDirectory, RemoteFile } from "@/api/remoteFiles";

import {
    basicEntryToItem,
    collectionToItem,
    datasetToItem,
    entryToSelectionItem,
    filesDialogEntryToItem,
    fileSourcePluginToItem,
    historyToItem,
    toDate,
} from "./selectionAdapters";

const ISO_TIME = "2026-10-17T09:30:00.000Z";

function getFakeDataset(data: Partial<HDASummary> = {}): HDASummary {
    return {
        id: "fake_dataset_id",
        name: "Unnamed dataset",
        create_time: ISO_TIME,
        dataset_id: "fake_dataset_id",
        deleted: false,
        extension: "txt",
        genome_build: null,
        hid: 1,
        history_content_type: "dataset",
        history_id: "fake_history_id",
        purged: false,
        state: "ok",
        tags: [],
        type: "file",
        update_time: ISO_TIME,
        url: "/api/datasets/fake_dataset_id",
        visible: true,
        ...data,
    };
}

describe("toDate", () => {
    it("parses a valid timestamp", () => {
        expect(toDate(ISO_TIME)?.getTime()).toBe(Date.parse(ISO_TIME));
    });

    it.each([[""], [null], [undefined], ["not a date"]])("returns undefined for %j", (value) => {
        expect(toDate(value)).toBeUndefined();
    });
});

describe("historyToItem", () => {
    const history = getFakeHistorySummary({
        id: "h1",
        name: "My history",
        annotation: null,
        url: "/api/histories/h1",
        count: 4,
        tags: ["name:rna"],
        update_time: ISO_TIME,
    });

    it("maps a history to a folder item", () => {
        expect(historyToItem(history)).toEqual({
            id: "h1",
            label: "My history",
            details: "",
            isLeaf: false,
            url: "/api/histories/h1",
            size: 4,
            tags: ["name:rna"],
            update_time: ISO_TIME,
            updateTime: new Date(ISO_TIME),
            entry: history,
        });
    });
});

describe("datasetToItem", () => {
    it("maps a dataset to a leaf item", () => {
        const dataset = getFakeDataset({
            id: "d1",
            name: "reads.fastq",
            url: "/api/datasets/d1",
            tags: ["group:a"],
            update_time: ISO_TIME,
        });
        expect(datasetToItem(dataset)).toEqual({
            id: "d1",
            label: "reads.fastq",
            details: "",
            isLeaf: true,
            url: "/api/datasets/d1",
            tags: ["group:a"],
            update_time: ISO_TIME,
            updateTime: new Date(ISO_TIME),
            entry: dataset,
        });
    });

    it("keeps a dataset without name or update time", () => {
        const dataset = getFakeDataset({ id: "d2", name: null, url: "", update_time: null });
        const item = datasetToItem(dataset);
        expect(item.label).toBe("");
        expect(item.updateTime).toBeUndefined();
    });
});

describe("collectionToItem", () => {
    it("maps a collection to a leaf item", () => {
        const collection = { id: "c1", name: "pairs", hid: 3, created_time: ISO_TIME };
        expect(collectionToItem(collection)).toEqual({
            id: "c1",
            label: "pairs",
            details: "",
            isLeaf: true,
            url: "",
            time: ISO_TIME,
            updateTime: new Date(ISO_TIME),
            entry: collection,
        });
    });
});

describe("basicEntryToItem", () => {
    const keys = { labelKey: "title", detailsKey: "info", timeKey: "update_time" };

    it("reads label, details and time from the configured keys", () => {
        const entry = { id: "b1", title: "Page", info: "about", update_time: ISO_TIME };
        expect(basicEntryToItem(entry, keys)).toEqual({
            id: "b1",
            label: "Page",
            details: "about",
            isLeaf: true,
            url: "",
            time: ISO_TIME,
            updateTime: new Date(ISO_TIME),
            entry: entry,
        });
    });

    it("leaves missing values empty", () => {
        const item = basicEntryToItem({ id: "b2" }, keys);
        expect(item.label).toBeNull();
        expect(item.details).toBeNull();
        expect(item.time).toBeNull();
        expect(item.updateTime).toBeUndefined();
    });
});

describe("file source adapters", () => {
    it("maps a file source plugin to a folder item", () => {
        const plugin = { id: "ftp", label: "FTP", doc: "Your FTP", uri_root: "gxftp://" } as BrowsableFilesSourcePlugin;
        expect(fileSourcePluginToItem(plugin)).toEqual({
            id: "ftp",
            label: "FTP",
            details: "Your FTP",
            isLeaf: false,
            url: "gxftp://",
            entry: plugin,
        });
    });

    const file = {
        class: "File",
        name: "a.txt",
        uri: "gxftp://a.txt",
        path: "a.txt",
        size: 12,
        ctime: ISO_TIME,
    } as RemoteFile;
    const directory = { class: "Directory", name: "dir", uri: "gxftp://dir", path: "dir" } as RemoteDirectory;

    it("maps a remote file for the file browser", () => {
        expect(entryToSelectionItem(file)).toEqual({
            id: "gxftp://a.txt",
            label: "a.txt",
            url: "gxftp://a.txt",
            isLeaf: true,
            details: "",
            entry: file,
        });
        expect(entryToSelectionItem(directory)).toEqual({
            id: "gxftp://dir",
            label: "dir",
            url: "gxftp://dir",
            isLeaf: false,
            details: "",
            entry: directory,
        });
    });

    it("maps a remote file for the files dialog with its creation time and size", () => {
        expect(filesDialogEntryToItem(file)).toEqual({
            id: "gxftp://a.txt",
            label: "a.txt",
            time: ISO_TIME,
            details: ISO_TIME,
            isLeaf: true,
            url: "gxftp://a.txt",
            size: 12,
            updateTime: new Date(ISO_TIME),
            entry: file,
        });
    });

    it("maps a remote directory for the files dialog without time or size", () => {
        expect(filesDialogEntryToItem(directory)).toEqual({
            id: "gxftp://dir",
            label: "dir",
            time: "",
            details: "",
            isLeaf: false,
            url: "gxftp://dir",
            size: 0,
            updateTime: undefined,
            entry: directory,
        });
    });
});

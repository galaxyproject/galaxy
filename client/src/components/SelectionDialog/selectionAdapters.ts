import type { HDASummary, HistorySummary } from "@/api";
import type { BrowsableFilesSourcePlugin, RemoteEntry } from "@/api/remoteFiles";

import type { SelectionItem } from "./selectionTypes";

export interface HistorySelectionItem extends SelectionItem {
    size: number;
    update_time: string;
}

export interface DatasetSelectionItem extends SelectionItem {
    update_time: string | null;
}

export interface CollectionEntry {
    id: string;
    name: string;
    created_time: string;
    hid: number;
    collection_type?: string;
}

export interface TimedSelectionItem extends SelectionItem {
    time: string | null;
}

export interface BasicEntryKeys {
    detailsKey: string;
    labelKey: string;
    timeKey: string;
}

/** Parses an API timestamp; empty or unparsable values give undefined so the dialog shows "-". */
export function toDate(value?: string | null): Date | undefined {
    if (!value) {
        return undefined;
    }
    const date = new Date(value);
    return isNaN(date.getTime()) ? undefined : date;
}

export function historyToItem(entry: HistorySummary): HistorySelectionItem {
    return {
        id: entry.id,
        label: entry.name,
        details: entry.annotation || "",
        isLeaf: false,
        url: entry.url,
        size: entry.count,
        tags: entry.tags,
        update_time: entry.update_time,
        updateTime: toDate(entry.update_time),
        entry: entry,
    };
}

export function datasetToItem(entry: HDASummary): DatasetSelectionItem {
    return {
        id: entry.id,
        label: entry.name || "",
        details: "",
        isLeaf: true,
        url: entry.url,
        tags: entry.tags,
        update_time: entry.update_time,
        updateTime: toDate(entry.update_time),
        entry: entry,
    };
}

export function collectionToItem(entry: CollectionEntry): TimedSelectionItem {
    return {
        id: entry.id,
        label: entry.name,
        details: "",
        isLeaf: true,
        url: "",
        time: entry.created_time,
        updateTime: toDate(entry.created_time),
        entry: entry as unknown as Record<string, unknown>,
    };
}

/** Maps a record of BasicSelectionDialog's `getData()`, reading label, details and time from the configured keys. */
export function basicEntryToItem(entry: Record<string, any>, keys: BasicEntryKeys): TimedSelectionItem {
    const timeStamp = entry[keys.timeKey];
    return {
        id: entry.id,
        label: entry[keys.labelKey] || null,
        details: entry[keys.detailsKey] || null,
        isLeaf: true,
        url: "",
        time: timeStamp || null,
        updateTime: toDate(timeStamp),
        entry: entry,
    };
}

export function fileSourcePluginToItem(plugin: BrowsableFilesSourcePlugin): SelectionItem {
    const result = {
        id: plugin.id,
        label: plugin.label,
        details: plugin.doc || "",
        isLeaf: false,
        url: plugin.uri_root,
        entry: plugin,
    };
    return result;
}

/**
 * Maps a RemoteEntry (file or directory) to a SelectionItem for use in the file browser.
 */
export function entryToSelectionItem(entry: RemoteEntry): SelectionItem {
    return {
        id: entry.uri,
        label: entry.name,
        url: entry.uri,
        isLeaf: entry.class === "File",
        details: "",
        entry: entry as unknown as Record<string, unknown>,
    };
}

/** Maps a RemoteEntry for FilesDialog, which also lists the file creation time and size. */
export function filesDialogEntryToItem(entry: RemoteEntry): TimedSelectionItem {
    const time = entry.class === "File" ? (entry.ctime ?? "") : "";
    return {
        id: entry.uri,
        label: entry.name,
        time: time,
        details: time,
        isLeaf: entry.class === "File",
        url: entry.uri,
        size: entry.class === "File" ? entry.size : 0,
        updateTime: toDate(time),
        entry: entry as unknown as Record<string, unknown>,
    };
}

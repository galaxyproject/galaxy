/**
 * Model to track selected URI for FilesDialog - mirroring DataDialog's model.
 */
import { isSubPath } from "@/components/FilesDialog/utilities";

export interface BaseRecordItem {
    id: string;
    label: string;
    details: string;
    isLeaf: boolean;
    url: string;
    labelTitle: string | undefined;
}

export interface FileRecord extends BaseRecordItem {
    isLeaf: true;
}

export interface DirectoryRecord extends BaseRecordItem {
    isLeaf: false;
}

interface ModelOptions {
    multiple?: boolean;
}

export type RecordItem = FileRecord | DirectoryRecord;

export class Model {
    private values: Record<string, BaseRecordItem>;
    private multiple: boolean;

    constructor(options: ModelOptions = {}) {
        this.values = {};
        this.multiple = options.multiple || false;
    }

    /** Adds a new record to the value stack **/
    add(record: BaseRecordItem) {
        if (!this.multiple) {
            this.values = {};
        }
        const key = record.id;
        if (key) {
            if (!this.values[key]) {
                this.values[key] = record;
            } else {
                delete this.values[key];
            }
        } else {
            throw Error("Invalid record with no <id>.");
        }
    }

    /** Returns the number of added records **/
    count() {
        return Object.keys(this.values).length;
    }

    /** Returns true if a record is available for a given key **/
    exists(key: string) {
        return !!this.values[key];
    }

    /** Returns true if a record under given path exists **/
    pathExists(path: string) {
        return Object.values(this.values).some((value) => {
            return isSubPath(path, value.url);
        });
    }

    /** unselect all files under this path **/
    unselectUnderPath(path: string) {
        Object.keys(this.values).forEach((key) => {
            const value = this.values[key];
            if (value && isSubPath(path, value.url)) {
                delete this.values[key];
            }
        });
    }

    /** Finalizes the results from added records **/
    finalize(): BaseRecordItem | BaseRecordItem[] {
        const results: BaseRecordItem[] = [];
        Object.values(this.values).forEach((v) => {
            results.push(v);
        });
        if (results.length > 0 && !this.multiple) {
            return results.at(0) as BaseRecordItem;
        }
        return results;
    }
}

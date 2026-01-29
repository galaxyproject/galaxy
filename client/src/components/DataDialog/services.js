import axios from "axios";
import { getAppRoot } from "onload/loadConfig";

/** Data populator traverses raw server responses **/
export class Services {
    get(url) {
        return new Promise((resolve, reject) => {
            axios
                .get(url)
                .then((response) => {
                    const items = this.getItems(response.data);
                    resolve(items);
                })
                .catch((e) => {
                    let errorMessage = "Request failed.";
                    if (e.response) {
                        errorMessage = e.response.data.err_msg || `${e.response.statusText} (${e.response.status})`;
                    }
                    reject(errorMessage);
                });
        });
    }

    /** Returns the formatted results **/
    getItems(data) {
        const items = [];
        const stack = [data];
        while (stack.length > 0) {
            const root = stack.pop();
            if (Array.isArray(root)) {
                root.forEach((element) => {
                    stack.push(element);
                });
            } else if (root.elements) {
                stack.push(root.elements);
            } else if (root.object) {
                stack.push(root.object);
            } else {
                const record = this.getRecord(root);
                if (record) {
                    items.push(record);
                }
            }
        }
        return items;
    }

    /** Populate record data from raw record source **/
    getRecord(record) {
        const host = `${window.location.protocol}//${window.location.hostname}:${window.location.port}`;
        record.extension = record.extension ?? record.file_ext;
        record.details = record.extension || record.description;
        record.time = record.update_time || record.create_time;
        record.isLeaf = this.isDataset(record);
        if (record.time) {
            record.time = record.time.substring(0, 16).replace("T", " ");
        }
        if (record.model_class == "Library") {
            record.label = record.name;
            record.url = `${getAppRoot()}api/libraries/${record.id}/contents`;
            return record;
        } else if (record.hid) {
            record.label = `${record.hid}: ${record.name}`;
            record.download = `${host}${getAppRoot()}api/histories/${record.history_id}/contents/${record.id}/display`;
            return record;
        } else if (record.type == "file") {
            record.src = "ldda";
            record.label = record.name;
            record.download = `${host}${getAppRoot()}api/libraries/datasets/download/uncompressed?ld_ids=${record.id}`;
            return record;
        }
    }

    /** Checks if record is a dataset or drillable **/
    isDataset(record) {
        return record.history_content_type == "dataset" || record.type == "file";
    }
}

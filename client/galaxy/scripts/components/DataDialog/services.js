import axios from "axios";

/** Data populator traverses raw server responses **/
export class Services {
    constructor(options = {}) {
        this.root = options.root;
        this.host = options.host;
    }

    get(url) {
        return new Promise((resolve, reject) => {
            axios
                .get(url)
                .then(response => {
                    let items = this.getItems(response.data);
                    resolve(items);
                })
                .catch(e => {
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
        let items = [];
        let stack = [data];
        while (stack.length > 0) {
            let root = stack.pop();
            if (Array.isArray(root)) {
                root.forEach(element => {
                    stack.push(element);
                });
            } else if (root.elements) {
                stack.push(root.elements);
            } else if (root.object) {
                stack.push(root.object);
            } else {
                let record = this.getRecord(root);
                if (record) {
                    items.push(record);
                }
            }
        }
        return items;
    }

    /** Populate record data from raw record source **/
    getRecord(record) {
        record.details = record.extension || record.description;
        record.time = record.update_time || record.create_time;
        record.isDataset = this.isDataset(record);
        if (record.time) {
            record.time = record.time.substring(0, 16).replace("T", " ");
        }
        if (record.model_class == "Library") {
            record.url = `${this.root}api/libraries/${record.id}/contents`;
            return record;
        } else if (record.hid) {
            record.name = `${record.hid}: ${record.name}`;
            record.download = `${this.host}/api/histories/${record.history_id}/contents/${record.id}/display`;
            return record;
        } else if (record.type == "file") {
            if (record.name && record.name[0] === "/") {
                record.name = record.name.substring(1);
            }
            record.download = `${this.host}${this.root}api/libraries/datasets/download/uncompressed?ld_ids=${
                record.id
            }`;
            return record;
        }
    }

    /** Checks if record is a dataset or drillable **/
    isDataset(record) {
        return record.history_content_type == "dataset" || record.type == "file";
    }
}

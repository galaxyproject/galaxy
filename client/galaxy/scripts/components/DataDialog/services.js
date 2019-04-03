import { getGalaxyInstance } from "app";
import axios from "axios";
import { UrlTracker } from "./utilities";

export class Services {
    constructor() {
        this.galaxy = getGalaxyInstance();
        this.urlTracker = new UrlTracker(this.getHistoryUrl());
    }

    /** Returns the default url i.e. the url of the current history **/
    getHistoryUrl() {
        let historyId = this.galaxy.currHistoryPanel && this.galaxy.currHistoryPanel.model.id;
        if (historyId) {
            return `${this.galaxy.root}api/histories/${historyId}/contents?deleted=false`;
        }
    }

    /** Get raw data **/
    getData(url) {
        return new Promise((resolve, reject) => {
            url = this.urlTracker.getUrl(url);
            axios
                .get(url)
                .then(response => {
                    let items = this.getItems(response.data);
                    resolve(items);
                })
                .catch(e => {
                    let errorMessage = "Datasets not available.";
                    if (e.response) {
                        errorMessage = e.response.data.err_msg || `${e.response.statusText} (${e.response.status})`;
                    }
                    reject(e);
                });
        });
    }

    /** Build record url **/
    addHostToUrl(url) {
        return `${window.location.protocol}//${window.location.hostname}:${window.location.port}${url}`;
    }

    /** Populate record data from raw record source **/
    populateRecord(record) {
        record.details = record.extension || record.description;
        record.time = record.update_time || record.create_time;
        if (record.time) {
            record.time = record.time.substring(0, 16).replace("T", " ");
        }
        if (record.model_class == "Library") {
            record.url = `${this.galaxy.root}api/libraries/${record.id}/contents`;
            return record;
        } else if (record.hid) {
            record.name = `${record.hid}: ${record.name}`;
            record.download = this.addHostToUrl(`${record.url}/display`);
            return record;
        } else if (record.type == "file") {
            if (record.name && record.name[0] === "/") {
                record.name = record.name.substring(1);
            }
            let url = `${this.galaxy.root}api/libraries/datasets/download/uncompressed?ld_ids=${record.id}`;
            record.download = this.addHostToUrl(url);
            return record;
        }
    }

    /** Traverese raw records from server response **/
    getItems(data) {
        let items = [];
        if (this.library && this.services.atRoot()) {
            items.push({
                name: "Data Libraries",
                url: `${this.galaxy.root}api/libraries`
            });
        }
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
                let record = this.populateRecord(root);
                if (record) {
                    items.push(record);
                }
            }
        }
        return items;
    }
}

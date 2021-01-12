import { dateMixin, ModelBase } from "./ModelBase";

const defaults = {
    accessible: false,
    update_time: 0,
};

const contentTypes = {
    DATASET: "dataset",
    COLLECTION: "dataset_collection",
};

export class Content extends dateMixin(ModelBase) {
    loadProps(raw = {}) {
        const props = Object.assign({}, defaults, raw);
        super.loadProps(props);
    }

    get title() {
        const { name, isDeleted, visible, purged } = this;
        let result = name;
        const itemStates = [];
        if (isDeleted) {
            itemStates.push("Deleted");
        }
        if (visible == false) {
            itemStates.push("Hidden");
        }
        if (purged) {
            itemStates.push("Purged");
        }
        if (itemStates.length) {
            result += ` (${itemStates.join(", ")})`;
        }
        return result;
    }

    get deleted() {
        return this.isDeleted;
    }

    set deleted(newVal) {
        this.isDeleted = newVal;
    }

    get isDataset() {
        return this.history_content_type == contentTypes.DATASET;
    }

    get isCollection() {
        return this.history_content_type == contentTypes.COLLECTION;
    }

    get hda_id() {
        return this.isDataset ? this.id : null;
    }

    get hdca_id() {
        return this.isCollection ? this.id : null;
    }
}

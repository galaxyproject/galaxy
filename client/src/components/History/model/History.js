import { dateMixin, ModelBase } from "./ModelBase";
import { bytesToString } from "utils/utils";

export class History extends dateMixin(ModelBase) {
    // not deleted
    get active() {
        return !this.deleted && !this.purged;
    }

    get hidItems() {
        return parseInt(this.hid_counter) - 1;
    }

    get totalItems() {
        return Object.keys(this.contents_active).reduce((result, key) => {
            const val = this.contents_active[key];
            return result + parseInt(val);
        }, 0);
    }

    get niceSize() {
        return this.size ? bytesToString(this.size, true, 2) : "(empty)";
    }

    get statusDescription() {
        const status = [];
        if (this.shared) status.push("Shared");
        if (this.importable) status.push("Accessible");
        if (this.published) status.push("Published");
        if (this.isDeleted) status.push("Deleted");
        if (this.purged) status.push("Purged");
        return status.join(", ");
    }
}

History.equals = function (a, b) {
    return JSON.stringify(a) == JSON.stringify(b);
};

History.create = (...args) => {
    return Object.freeze(new History(...args));
};

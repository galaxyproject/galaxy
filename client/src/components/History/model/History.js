import { dateMixin, ModelBase } from "./ModelBase";
import { scrubModelProps } from "utils/safeAssign";

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

    get statusDescription() {
        const status = [];
        if (this.shared) {
            status.push("Shared");
        }
        if (this.importable) {
            status.push("Accessible");
        }
        if (this.published) {
            status.push("Published");
        }
        if (this.isDeleted) {
            status.push("Deleted");
        }
        if (this.purged) {
            status.push("Purged");
        }
        return status.join(", ");
    }

    get exportLink() {
        return `histories/${this.id}/export`;
    }

    clone() {
        const newProps = cleanHistoryProps(this);
        return new History(newProps);
    }

    patch(newProps) {
        const cleanProps = cleanHistoryProps({ ...this, ...newProps });
        return new History(cleanProps);
    }

    equals(other) {
        return History.equals(this, other);
    }
}

History.equals = function (a, b) {
    return JSON.stringify(a) == JSON.stringify(b);
};

const scrubber = scrubModelProps(History);
export const cleanHistoryProps = (props = {}) => {
    const cleanProps = JSON.parse(JSON.stringify(props));
    return scrubber(cleanProps);
};

import { scrubModelProps } from "utils/safeAssign";

export class History {
    constructor(doc = {}) {
        try {
            this.loadProps(doc);
        } catch (err) {
            console.debug("Unable to load history props.", doc);
            throw err;
        }
    }

    loadProps(raw = {}) {
        Object.assign(this, raw);
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

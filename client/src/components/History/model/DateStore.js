/**
 * Key/Date storage. Used to monitor the last time a certain URL
 * was requested in the content update mechanism.
 */

import moment from "moment";

const defaultDate = moment.utc(0);

export class DateStore extends Map {
    // don't store dates earlier than the latest existing value
    set(key, val = moment.utc()) {
        if (!moment.isMoment(val)) {
            throw new Error("Only store moment objects in the date store please");
        }
        const existing = this.get(key);
        return val.isBefore(existing) ? this : super.set(key, val);
    }

    get(key) {
        return this.has(key) ? super.get(key) : defaultDate;
    }
}

export function createDateStore(label = "Default") {
    const ds = new DateStore();
    ds.label = label;
    return ds;
}

/**
 * Key/Date storage
 */

import moment from "moment";
import { DateStore } from "./DateStore";
// import { show } from "jest/helpers";

describe("DateStore", () => {
    const defaultDate = moment.utc(0);

    let dateStore;
    beforeEach(() => (dateStore = new DateStore()));

    it("should return a default date value when key not present", () => {
        const lookup = dateStore.get("doesntexist");
        expect(moment.isMoment(lookup)).toBeTruthy();
        expect(lookup.isSame(defaultDate)).toBeTruthy();
    });

    it("should record a new utc date when set is called", () => {
        dateStore.set("abc");
        const lookup = dateStore.get("abc");
        expect(moment.isMoment(lookup)).toBeTruthy();
        expect(lookup.isAfter(defaultDate)).toBeTruthy();
    });

    it("should retrieve the last date when markDate is called", () => {
        const lastWeek = moment().subtract(7, "days");
        dateStore.set("abc", lastWeek);
        dateStore.set("abc");
        const lookup = dateStore.get("abc");
        expect(moment.isMoment(lookup)).toBe(true);
        expect(lookup.isAfter(lastWeek)).toBe(true);
        expect(lastWeek.isBefore(moment.now())).toBe(true);
        expect(lastWeek.isBefore(lookup)).toBe(true);
    });

    it("shouldn't mark an earlier date if the existing date is later", () => {
        dateStore.set("abc");
        dateStore.set("abc", defaultDate);
        const lookup = dateStore.get("abc");
        expect(moment.isMoment(lookup)).toBeTruthy();
        expect(lookup.isAfter(defaultDate)).toBeTruthy();
    });

    it("method: clear, should empty the storage when clear", () => {
        dateStore.set("abc");
        dateStore.clear();
        expect(dateStore.size == 0).toBeTruthy();
    });

    it("should throw an error if we try to save something that is not a moment object", () => {
        const badVal = Math.PI;
        expect(!moment.isMoment(badVal)).toBeTruthy();
        expect(() => dateStore.set("abc", badVal)).toThrow();
    });
});

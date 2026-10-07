import MockDate from "timezone-mock";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import {
    formatGalaxyPrettyDateString,
    galaxyTimeToDate,
    localizeUTCPretty,
    relativeUpdatedLabel,
    shortDateLabel,
} from "./dates";

describe("dates.ts", () => {
    beforeEach(() => {
        MockDate.register("Etc/GMT+4");
    });

    afterEach(() => {
        MockDate.unregister();
    });

    describe("galaxyTimeToDate", () => {
        it("should convert valid galaxyTime string to Date object", () => {
            const galaxyTime = "2023-10-01T12:00:00";
            const date = galaxyTimeToDate(galaxyTime);
            expect(date).toBeInstanceOf(Date);
            expect(date.toISOString()).toBe("2023-10-01T12:00:00.000Z");
        });

        it("should append Z if missing and parse correctly", () => {
            const galaxyTime = "2023-10-01T12:00:00";
            const date = galaxyTimeToDate(galaxyTime);
            expect(date.toISOString()).toBe("2023-10-01T12:00:00.000Z");
        });

        it("should throw an error for invalid galaxyTime string", () => {
            const invalidGalaxyTime = "invalid-date-string";
            expect(() => galaxyTimeToDate(invalidGalaxyTime)).toThrow(
                `Invalid galaxyTime string: ${invalidGalaxyTime}`,
            );
        });
    });

    describe("localizeUTCPretty", () => {
        it("should format Date object into human-readable string", () => {
            const date = new Date("2023-10-01T12:00:00Z");
            const formatted = localizeUTCPretty(date);
            expect(formatted).toBe("Sunday Oct 1st 8:00:00 2023 GMT-4");
        });
    });

    describe("formatGalaxyPrettyDateString", () => {
        it("should convert galaxyTime string to formatted date string", () => {
            const galaxyTime = "2023-10-01T12:00:00";
            const formatted = formatGalaxyPrettyDateString(galaxyTime);
            expect(formatted).toBe("Sunday Oct 1st 8:00:00 2023 GMT-4");
        });
    });

    describe("relativeUpdatedLabel", () => {
        it("should describe the time relative to now", () => {
            const threeDaysAgo = new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString().replace("Z", "");
            expect(relativeUpdatedLabel(threeDaysAgo)).toBe("updated 3 days ago");
        });

        it("should return undefined for a missing or malformed time", () => {
            expect(relativeUpdatedLabel(undefined)).toBeUndefined();
            expect(relativeUpdatedLabel(null)).toBeUndefined();
            expect(relativeUpdatedLabel("")).toBeUndefined();
            expect(relativeUpdatedLabel("invalid-date-string")).toBeUndefined();
        });
    });

    describe("shortDateLabel", () => {
        it("should format the time as a short date in the user's time zone", () => {
            expect(shortDateLabel("2023-10-01T12:00:00")).toBe("Oct 1, 2023");
            expect(shortDateLabel("2023-10-01T02:00:00")).toBe("Sep 30, 2023");
        });

        it("should return undefined for a missing or malformed time", () => {
            expect(shortDateLabel(undefined)).toBeUndefined();
            expect(shortDateLabel(null)).toBeUndefined();
            expect(shortDateLabel("")).toBeUndefined();
            expect(shortDateLabel("invalid-date-string")).toBeUndefined();
        });
    });
});

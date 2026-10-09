import MockDate from "timezone-mock";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

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
        vi.restoreAllMocks();
    });

    describe("galaxyTimeToDate", () => {
        it("parses a Galaxy UTC timestamp as a Date", () => {
            const galaxyTime = "2023-10-01T12:00:00";
            const date = galaxyTimeToDate(galaxyTime);
            expect(date).toBeInstanceOf(Date);
            expect(date.toISOString()).toBe("2023-10-01T12:00:00.000Z");
        });

        it("treats a timestamp without a Z suffix as UTC", () => {
            const galaxyTime = "2023-10-01T12:00:00";
            const date = galaxyTimeToDate(galaxyTime);
            expect(date.toISOString()).toBe("2023-10-01T12:00:00.000Z");
        });

        it("reports the original timestamp when parsing fails", () => {
            const invalidGalaxyTime = "invalid-date-string";
            expect(() => galaxyTimeToDate(invalidGalaxyTime)).toThrow(
                `Invalid galaxyTime string: ${invalidGalaxyTime}`,
            );
        });
    });

    describe("localizeUTCPretty", () => {
        it("formats a UTC date in the mocked GMT-4 time zone", () => {
            const date = new Date("2023-10-01T12:00:00Z");
            const formatted = localizeUTCPretty(date);
            expect(formatted).toBe("Sunday Oct 1st 8:00:00 2023 GMT-4");
        });
    });

    describe("formatGalaxyPrettyDateString", () => {
        it("formats a Galaxy UTC timestamp in the mocked GMT-4 time zone", () => {
            const galaxyTime = "2023-10-01T12:00:00";
            const formatted = formatGalaxyPrettyDateString(galaxyTime);
            expect(formatted).toBe("Sunday Oct 1st 8:00:00 2023 GMT-4");
        });
    });

    describe("relativeUpdatedLabel", () => {
        it("describes a timestamp three days before a fixed current time", () => {
            vi.spyOn(Date, "now").mockReturnValue(new Date("2023-10-04T12:00:00Z").getTime());
            const threeDaysAgo = "2023-10-01T12:00:00";
            expect(relativeUpdatedLabel(threeDaysAgo)).toBe("updated 3 days ago");
        });

        it.each([
            { caseName: "omitted timestamp", timestamp: undefined },
            { caseName: "null timestamp", timestamp: null },
            { caseName: "empty timestamp", timestamp: "" },
            { caseName: "malformed timestamp", timestamp: "invalid-date-string" },
        ])("returns undefined for $caseName", ({ timestamp }) => {
            expect(relativeUpdatedLabel(timestamp)).toBeUndefined();
        });
    });

    describe("shortDateLabel", () => {
        it.each([
            { caseName: "same calendar day", timestamp: "2023-10-01T12:00:00", expected: "Oct 1, 2023" },
            { caseName: "previous calendar day", timestamp: "2023-10-01T02:00:00", expected: "Sep 30, 2023" },
        ])("formats the $caseName in the mocked GMT-4 time zone", ({ timestamp, expected }) => {
            expect(shortDateLabel(timestamp)).toBe(expected);
        });

        it.each([
            { caseName: "omitted timestamp", timestamp: undefined },
            { caseName: "null timestamp", timestamp: null },
            { caseName: "empty timestamp", timestamp: "" },
            { caseName: "malformed timestamp", timestamp: "invalid-date-string" },
        ])("returns undefined for $caseName", ({ timestamp }) => {
            expect(shortDateLabel(timestamp)).toBeUndefined();
        });
    });
});

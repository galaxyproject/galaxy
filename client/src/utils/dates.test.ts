import { formatGalaxyPrettyDateString, galaxyTimeToDate, localizeUTCPretty } from "./dates";

describe("dates.ts", () => {
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
                `Invalid galaxyTime string: ${invalidGalaxyTime}`
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
});
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import Filtering, { compare, contains } from "@/utils/filtering";

import { CUSTOM_TIME_RANGE, getActiveTimeRange, setActiveTimeRange, type TimeRange } from "./timeRanges";

const DAY: TimeRange = { key: "24h", label: "Last 24 hours", durationMs: 24 * 60 * 60 * 1000 };

const filtering = new Filtering(
    {
        name: { placeholder: "name", type: String, handler: contains("name"), menuItem: true },
        create_time: {
            placeholder: "create time",
            type: Date,
            handler: compare("create_time", "le"),
            isRangeInput: true,
            menuItem: true,
        },
    },
    undefined,
    false,
);

describe("time range helpers", () => {
    beforeEach(() => {
        vi.useFakeTimers();
        vi.setSystemTime(new Date("2026-11-11T12:00:00.000Z"));
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it("applies a range as the filter's `_gt` cutoff from now, keeping other filters", () => {
        const { filterText, appliedRange } = setActiveTimeRange(filtering, "create_time", "name:rna", DAY);
        expect(filterText).toBe("name:rna create_time>2026-11-10T12:00:00.000Z");
        expect(appliedRange).toEqual({ key: "24h", value: "2026-11-10T12:00:00.000Z" });
        expect(getActiveTimeRange(filtering, "create_time", filterText, appliedRange)).toBe("24h");
    });

    it("clears the range for Anytime", () => {
        const set = setActiveTimeRange(filtering, "create_time", "name:rna", DAY);
        const cleared = setActiveTimeRange(filtering, "create_time", set.filterText, undefined);
        expect(cleared).toEqual({ filterText: "name:rna", appliedRange: undefined });
        expect(getActiveTimeRange(filtering, "create_time", cleared.filterText, undefined)).toBeUndefined();
    });

    it("treats a range typed by hand as custom", () => {
        const applied = setActiveTimeRange(filtering, "create_time", "", DAY).appliedRange;
        expect(getActiveTimeRange(filtering, "create_time", "create_time>2026-01-01", applied)).toBe(CUSTOM_TIME_RANGE);
        expect(getActiveTimeRange(filtering, "create_time", "create_time<2026-01-01", undefined)).toBe(
            CUSTOM_TIME_RANGE,
        );
    });
});

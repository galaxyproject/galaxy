import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { LIST_REFRESH_INTERVAL_MS, markListRefreshed, refreshListWhenStale, resetListRefreshTracking } from "./refresh";

describe("palette list refresh", () => {
    beforeEach(() => {
        resetListRefreshTracking();
        vi.useFakeTimers();
        vi.setSystemTime(new Date("2026-08-31T10:00:00Z"));
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it("refreshes a list the palette has not refreshed yet", () => {
        const refresh = vi.fn().mockResolvedValue(undefined);

        refreshListWhenStale("workflows:my", refresh);

        expect(refresh).toHaveBeenCalledTimes(1);
    });

    it("serves a freshly fetched list without asking again", () => {
        const refresh = vi.fn().mockResolvedValue(undefined);
        markListRefreshed("workflows:my");

        refreshListWhenStale("workflows:my", refresh);
        vi.advanceTimersByTime(LIST_REFRESH_INTERVAL_MS - 1);
        refreshListWhenStale("workflows:my", refresh);

        expect(refresh).not.toHaveBeenCalled();
    });

    it("refreshes again once the interval has passed", () => {
        const refresh = vi.fn().mockResolvedValue(undefined);
        markListRefreshed("workflows:my");

        vi.advanceTimersByTime(LIST_REFRESH_INTERVAL_MS);
        refreshListWhenStale("workflows:my", refresh);

        expect(refresh).toHaveBeenCalledTimes(1);
    });

    it("tracks each list separately", () => {
        const refresh = vi.fn().mockResolvedValue(undefined);
        markListRefreshed("workflows:my");

        refreshListWhenStale("workflows:my", refresh);
        refreshListWhenStale("workflows:shared", refresh);

        expect(refresh).toHaveBeenCalledTimes(1);
    });

    it("swallows a failing refresh instead of rejecting", async () => {
        const refresh = vi.fn().mockRejectedValue(new Error("boom"));

        expect(() => refreshListWhenStale("workflows:my", refresh)).not.toThrow();
        await vi.runAllTimersAsync();

        expect(refresh).toHaveBeenCalledTimes(1);
    });
});

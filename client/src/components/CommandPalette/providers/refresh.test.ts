import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { LIST_REFRESH_INTERVAL_MS, markListRefreshed, refreshListWhenStale, resetListRefreshTracking } from "./refresh";

const MY_WORKFLOWS = "workflows:my";
const SHARED_WORKFLOWS = "workflows:shared";

function succeedingRefresh() {
    return vi.fn().mockResolvedValue(undefined);
}

describe("palette list refresh", () => {
    beforeEach(() => {
        resetListRefreshTracking();
        vi.useFakeTimers();
        vi.setSystemTime(new Date("2026-08-31T10:00:00Z"));
    });

    afterEach(() => {
        vi.useRealTimers();
        vi.restoreAllMocks();
    });

    it("refreshes a list the palette has not refreshed yet", () => {
        const refresh = succeedingRefresh();

        refreshListWhenStale(MY_WORKFLOWS, refresh);

        expect(refresh).toHaveBeenCalledTimes(1);
    });

    it("serves a freshly fetched list without asking again", () => {
        const refresh = succeedingRefresh();
        markListRefreshed(MY_WORKFLOWS);

        refreshListWhenStale(MY_WORKFLOWS, refresh);
        vi.advanceTimersByTime(LIST_REFRESH_INTERVAL_MS - 1);
        refreshListWhenStale(MY_WORKFLOWS, refresh);

        expect(refresh).not.toHaveBeenCalled();
    });

    it("refreshes again once the interval has passed", () => {
        const refresh = succeedingRefresh();
        markListRefreshed(MY_WORKFLOWS);

        vi.advanceTimersByTime(LIST_REFRESH_INTERVAL_MS);
        refreshListWhenStale(MY_WORKFLOWS, refresh);

        expect(refresh).toHaveBeenCalledTimes(1);
    });

    it("tracks each list separately", () => {
        const refreshMine = succeedingRefresh();
        const refreshShared = succeedingRefresh();
        markListRefreshed(MY_WORKFLOWS);

        refreshListWhenStale(MY_WORKFLOWS, refreshMine);
        refreshListWhenStale(SHARED_WORKFLOWS, refreshShared);

        expect(refreshMine).not.toHaveBeenCalled();
        expect(refreshShared).toHaveBeenCalledTimes(1);
    });

    it("logs a failing refresh at debug level instead of rejecting", async () => {
        const debug = vi.spyOn(console, "debug").mockImplementation(() => {});
        const error = new Error("boom");
        const refresh = vi.fn().mockRejectedValue(error);

        refreshListWhenStale(MY_WORKFLOWS, refresh);
        await vi.runAllTimersAsync();

        expect(refresh).toHaveBeenCalledTimes(1);
        expect(debug).toHaveBeenCalledWith("Command palette could not refresh a cached list", MY_WORKFLOWS, error);
    });
});

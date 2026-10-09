import { wait } from "@tests/vitest/helpers";
import type { MockedFunction, MockInstance } from "@vitest/spy";
import flushPromises from "flush-promises";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useResourceWatcher, type WatchOptions, type WatchResourceHandler } from "./resourceWatcher";

describe("useResourceWatcher", () => {
    let mockWatchHandler: MockedFunction<WatchResourceHandler>;
    let addEventListenerSpy: MockInstance<typeof document.addEventListener>;
    let removeEventListenerSpy: MockInstance<typeof document.removeEventListener>;
    let visibilityState: DocumentVisibilityState;
    let watchers: ReturnType<typeof useResourceWatcher>[];

    beforeEach(() => {
        vi.useFakeTimers();
        mockWatchHandler = vi.fn<WatchResourceHandler>().mockResolvedValue();
        visibilityState = "visible";
        watchers = [];
        vi.spyOn(document, "visibilityState", "get").mockImplementation(() => visibilityState);
        addEventListenerSpy = vi.spyOn(document, "addEventListener");
        removeEventListenerSpy = vi.spyOn(document, "removeEventListener");
    });

    afterEach(() => {
        for (const watcher of watchers) {
            watcher.dispose();
        }
        vi.clearAllTimers();
        vi.useRealTimers();
        vi.restoreAllMocks();
    });

    function createWatcher(handler = mockWatchHandler, options?: WatchOptions) {
        const watcher = useResourceWatcher(handler, options);
        watchers.push(watcher);
        return watcher;
    }

    function changeVisibility(state: DocumentVisibilityState) {
        visibilityState = state;
        document.dispatchEvent(new Event("visibilitychange"));
    }

    function createSlowHandler(durationMs: number) {
        return vi.fn<WatchResourceHandler>().mockImplementation(async () => {
            await wait(durationMs);
        });
    }

    describe("basic functionality", () => {
        it("calls the watch handler immediately when started", () => {
            const { startWatchingResource } = createWatcher();

            startWatchingResource();

            expect(mockWatchHandler).toHaveBeenCalledTimes(1);
            expect(mockWatchHandler).toHaveBeenCalledWith(undefined);
        });

        it("passes the app to the watch handler", () => {
            const mockApp = { id: "test-app" };
            const { startWatchingResource } = createWatcher();

            startWatchingResource(mockApp);

            expect(mockWatchHandler).toHaveBeenCalledWith(mockApp);
        });

        it("stops polling after stopWatchingResource", async () => {
            const { startWatchingResource, stopWatchingResource } = createWatcher();

            startWatchingResource();
            expect(mockWatchHandler).toHaveBeenCalledTimes(1);

            stopWatchingResource();

            await vi.advanceTimersByTimeAsync(60000);

            expect(mockWatchHandler).toHaveBeenCalledTimes(1);
        });

        it("reports whether the watcher is started or stopped", () => {
            const { startWatchingResource, stopWatchingResource, isWatchingResource } = createWatcher();

            expect(isWatchingResource.value).toBe(false);

            startWatchingResource();
            expect(isWatchingResource.value).toBe(true);

            stopWatchingResource();
            expect(isWatchingResource.value).toBe(false);
        });
    });

    describe("polling intervals", () => {
        it("polls every 3000ms while visible by default", async () => {
            const { startWatchingResource } = createWatcher();

            startWatchingResource();
            await flushPromises();
            expect(mockWatchHandler).toHaveBeenCalledTimes(1);

            await vi.advanceTimersByTimeAsync(3000);

            expect(mockWatchHandler).toHaveBeenCalledTimes(2);

            await vi.advanceTimersByTimeAsync(3000);

            expect(mockWatchHandler).toHaveBeenCalledTimes(3);
        });

        it("uses a custom short polling interval", async () => {
            const customOptions: WatchOptions = {
                shortPollingInterval: 1500,
            };
            const { startWatchingResource } = createWatcher(mockWatchHandler, customOptions);

            startWatchingResource();
            await flushPromises();
            expect(mockWatchHandler).toHaveBeenCalledTimes(1);

            await vi.advanceTimersByTimeAsync(1500);

            expect(mockWatchHandler).toHaveBeenCalledTimes(2);
        });

        it("switches to the default 10000ms interval after the pending short poll when hidden", async () => {
            const { startWatchingResource } = createWatcher();

            startWatchingResource();
            await flushPromises();
            expect(mockWatchHandler).toHaveBeenCalledTimes(1);

            expect(addEventListenerSpy).toHaveBeenCalledWith("visibilitychange", expect.any(Function));

            changeVisibility("hidden");

            // Visibility changes affect the next interval, not the already scheduled poll.
            await vi.advanceTimersByTimeAsync(3000);
            expect(mockWatchHandler).toHaveBeenCalledTimes(2);

            await vi.advanceTimersByTimeAsync(10000);
            expect(mockWatchHandler).toHaveBeenCalledTimes(3);
        });

        it("uses a custom long interval after the pending short poll when hidden", async () => {
            const customOptions: WatchOptions = {
                longPollingInterval: 5000,
            };
            const { startWatchingResource } = createWatcher(mockWatchHandler, customOptions);

            startWatchingResource();
            await flushPromises();
            expect(mockWatchHandler).toHaveBeenCalledTimes(1);

            changeVisibility("hidden");

            // Visibility changes affect the next interval, not the already scheduled poll.
            await vi.advanceTimersByTimeAsync(3000);
            expect(mockWatchHandler).toHaveBeenCalledTimes(2);

            await vi.advanceTimersByTimeAsync(5000);

            expect(mockWatchHandler).toHaveBeenCalledTimes(3);
        });

        it("stops polling when hidden and background polling is disabled", async () => {
            const customOptions: WatchOptions = {
                enableBackgroundPolling: false,
            };
            const { startWatchingResource } = createWatcher(mockWatchHandler, customOptions);

            startWatchingResource();
            expect(mockWatchHandler).toHaveBeenCalledTimes(1);

            changeVisibility("hidden");

            await vi.advanceTimersByTimeAsync(30000);

            expect(mockWatchHandler).toHaveBeenCalledTimes(1);
        });
    });

    describe("visibility change handling", () => {
        it("registers one visibility listener per watcher instance", () => {
            createWatcher();
            createWatcher();

            expect(addEventListenerSpy).toHaveBeenCalledTimes(2);
            expect(addEventListenerSpy).toHaveBeenCalledWith("visibilitychange", expect.any(Function));
        });

        it("returns to short polling when visible without restarting the active watcher", async () => {
            const { startWatchingResource } = createWatcher();

            startWatchingResource();
            await flushPromises();
            expect(mockWatchHandler).toHaveBeenCalledTimes(1);

            changeVisibility("hidden");

            mockWatchHandler.mockClear();

            changeVisibility("visible");

            await flushPromises();
            expect(mockWatchHandler).toHaveBeenCalledTimes(0);

            await vi.advanceTimersByTimeAsync(3000);

            expect(mockWatchHandler).toHaveBeenCalledTimes(1);
        });
    });

    describe("error handling", () => {
        it("warns on a rejected request and continues polling", async () => {
            const consoleWarnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
            const error = new Error("Network error");
            mockWatchHandler.mockRejectedValueOnce(error).mockResolvedValue(undefined);

            const { startWatchingResource } = createWatcher();

            startWatchingResource();
            await flushPromises();

            expect(consoleWarnSpy).toHaveBeenCalledWith(error);
            expect(mockWatchHandler).toHaveBeenCalledTimes(1);

            await vi.advanceTimersByTimeAsync(3000);

            expect(mockWatchHandler).toHaveBeenCalledTimes(2);
        });

        it("continues polling after consecutive rejected requests", async () => {
            const consoleWarnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
            const error1 = new Error("First error");
            const error2 = new Error("Second error");

            mockWatchHandler.mockRejectedValueOnce(error1).mockRejectedValueOnce(error2).mockResolvedValue(undefined);

            const { startWatchingResource } = createWatcher();

            startWatchingResource();
            await flushPromises();

            expect(consoleWarnSpy).toHaveBeenCalledWith(error1);

            await vi.advanceTimersByTimeAsync(3000);

            expect(consoleWarnSpy).toHaveBeenCalledWith(error2);

            await vi.advanceTimersByTimeAsync(3000);

            expect(mockWatchHandler).toHaveBeenCalledTimes(3);
        });
    });

    describe("cleanup and resource management", () => {
        it("replaces the pending timeout when restarted", async () => {
            const { startWatchingResource } = createWatcher();

            startWatchingResource();
            await flushPromises();
            expect(mockWatchHandler).toHaveBeenCalledTimes(1);

            startWatchingResource();
            await flushPromises();
            expect(mockWatchHandler).toHaveBeenCalledTimes(2);

            await vi.advanceTimersByTimeAsync(3000);

            expect(mockWatchHandler).toHaveBeenCalledTimes(3);
        });

        it("stays stopped when a 5000ms request finishes after stopping", async () => {
            const slowHandler = createSlowHandler(5000);

            const { startWatchingResource, stopWatchingResource } = createWatcher(slowHandler);

            startWatchingResource();
            expect(slowHandler).toHaveBeenCalledTimes(1);

            await vi.advanceTimersByTimeAsync(2000);

            stopWatchingResource();

            await vi.advanceTimersByTimeAsync(3000);

            await vi.advanceTimersByTimeAsync(10000);

            expect(slowHandler).toHaveBeenCalledTimes(1);
        });

        it("does not overlap polls while an 8000ms request is pending or restart after stopping", async () => {
            const slowHandler = createSlowHandler(8000);

            const { startWatchingResource, stopWatchingResource } = createWatcher(slowHandler);

            startWatchingResource();
            expect(slowHandler).toHaveBeenCalledTimes(1);

            await vi.advanceTimersByTimeAsync(3000);

            expect(slowHandler).toHaveBeenCalledTimes(1);

            stopWatchingResource();

            await vi.advanceTimersByTimeAsync(5000);

            await vi.advanceTimersByTimeAsync(3000);

            expect(slowHandler).toHaveBeenCalledTimes(1);
        });

        it("reports the stopped state even after an in-flight request finishes", async () => {
            const slowHandler = createSlowHandler(5000);

            const { startWatchingResource, stopWatchingResource, isWatchingResource } = createWatcher(slowHandler);

            startWatchingResource();
            expect(isWatchingResource.value).toBe(true);

            await vi.advanceTimersByTimeAsync(2000);
            expect(isWatchingResource.value).toBe(true);

            stopWatchingResource();
            expect(isWatchingResource.value).toBe(false);

            await vi.advanceTimersByTimeAsync(10000);
            expect(isWatchingResource.value).toBe(false);
        });

        it("removes the visibility listener on dispose and stays stopped", async () => {
            const { startWatchingResource, dispose } = createWatcher();

            startWatchingResource();
            await flushPromises();
            expect(mockWatchHandler).toHaveBeenCalledTimes(1);

            const visibilityChangeHandler = addEventListenerSpy.mock.calls.find(
                ([event]) => event === "visibilitychange",
            )?.[1];
            expect(visibilityChangeHandler).toEqual(expect.any(Function));
            dispose();

            expect(removeEventListenerSpy).toHaveBeenCalledWith("visibilitychange", visibilityChangeHandler);

            mockWatchHandler.mockClear();
            await vi.advanceTimersByTimeAsync(60000);

            expect(mockWatchHandler).not.toHaveBeenCalled();
        });

        it("does not schedule another poll when hiding disables the interval", async () => {
            const customOptions: WatchOptions = {
                enableBackgroundPolling: false,
            };
            const { startWatchingResource } = createWatcher(mockWatchHandler, customOptions);

            startWatchingResource();

            changeVisibility("hidden");

            mockWatchHandler.mockClear();

            await vi.advanceTimersByTimeAsync(60000);

            expect(mockWatchHandler).not.toHaveBeenCalled();
        });
    });

    describe("integration scenarios", () => {
        it("uses custom visible and hidden intervals with background polling enabled", async () => {
            const customOptions: WatchOptions = {
                shortPollingInterval: 1000,
                longPollingInterval: 4000,
                enableBackgroundPolling: true,
            };
            const { startWatchingResource } = createWatcher(mockWatchHandler, customOptions);

            startWatchingResource();
            await flushPromises();
            expect(mockWatchHandler).toHaveBeenCalledTimes(1);

            await vi.advanceTimersByTimeAsync(1000);
            expect(mockWatchHandler).toHaveBeenCalledTimes(2);

            changeVisibility("hidden");

            // Finish the pending short poll before the new hidden interval begins.
            await vi.advanceTimersByTimeAsync(1000);
            expect(mockWatchHandler).toHaveBeenCalledTimes(3);

            await vi.advanceTimersByTimeAsync(4000);
            expect(mockWatchHandler).toHaveBeenCalledTimes(4);
        });

        it("changes intervals without restarting on rapid visibility changes", async () => {
            const { startWatchingResource } = createWatcher();

            startWatchingResource();
            await flushPromises();
            expect(mockWatchHandler).toHaveBeenCalledTimes(1);

            changeVisibility("hidden");

            changeVisibility("visible");
            await flushPromises();
            expect(mockWatchHandler).toHaveBeenCalledTimes(1);

            await vi.advanceTimersByTimeAsync(3000);
            expect(mockWatchHandler).toHaveBeenCalledTimes(2);

            changeVisibility("hidden");

            await vi.advanceTimersByTimeAsync(10000);
            expect(mockWatchHandler).toHaveBeenCalledTimes(3);
        });
    });
});

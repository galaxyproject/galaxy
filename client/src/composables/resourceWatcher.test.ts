import { jest } from "@jest/globals";
import flushPromises from "flush-promises";

import { useResourceWatcher, type WatchOptions, type WatchResourceHandler } from "./resourceWatcher";

// Mock the global document object
const mockAddEventListener = jest.fn();
const mockRemoveEventListener = jest.fn();

interface MockDocument {
    addEventListener: jest.MockedFunction<typeof document.addEventListener>;
    removeEventListener: jest.MockedFunction<typeof document.removeEventListener>;
    visibilityState: "visible" | "hidden";
}

const mockDocument: MockDocument = {
    addEventListener: mockAddEventListener,
    removeEventListener: mockRemoveEventListener,
    visibilityState: "visible",
};

Object.defineProperty(global, "document", {
    value: mockDocument,
    writable: true,
});

// Mock setTimeout and clearTimeout
jest.useFakeTimers();

// Helper function to get visibility change handler with proper typing
function getVisibilityChangeHandler(): () => void {
    const call = mockAddEventListener.mock.calls.find((call) => call[0] === "visibilitychange");
    return call?.[1] as () => void;
}

describe("useResourceWatcher", () => {
    let mockWatchHandler: jest.MockedFunction<WatchResourceHandler>;

    beforeEach(() => {
        jest.clearAllTimers();
        jest.clearAllMocks();
        mockWatchHandler = jest.fn<WatchResourceHandler>().mockResolvedValue();
        mockAddEventListener.mockClear();
        mockRemoveEventListener.mockClear();
        // Reset document visibility state
        mockDocument.visibilityState = "visible";
    });

    afterEach(() => {
        jest.runOnlyPendingTimers();
        jest.useRealTimers();
        jest.useFakeTimers();
    });

    describe("basic functionality", () => {
        it("should call the watch handler immediately when starting", async () => {
            const { startWatchingResource } = useResourceWatcher(mockWatchHandler);

            startWatchingResource();

            expect(mockWatchHandler).toHaveBeenCalledTimes(1);
            expect(mockWatchHandler).toHaveBeenCalledWith(undefined);
        });

        it("should pass the app parameter to the watch handler", async () => {
            const mockApp = { id: "test-app" };
            const { startWatchingResource } = useResourceWatcher(mockWatchHandler);

            startWatchingResource(mockApp);

            expect(mockWatchHandler).toHaveBeenCalledWith(mockApp);
        });

        it("should stop watching when stopWatchingResource is called", async () => {
            const { startWatchingResource, stopWatchingResource } = useResourceWatcher(mockWatchHandler);

            startWatchingResource();
            expect(mockWatchHandler).toHaveBeenCalledTimes(1);

            stopWatchingResource();

            // Fast-forward time to ensure no more calls are made
            jest.advanceTimersByTime(60000);
            await flushPromises();

            expect(mockWatchHandler).toHaveBeenCalledTimes(1);
        });

        it("should return correct value for isWatchingResource", async () => {
            const { startWatchingResource, stopWatchingResource, isWatchingResource } =
                useResourceWatcher(mockWatchHandler);

            expect(isWatchingResource.value).toBe(false);

            startWatchingResource();
            expect(isWatchingResource.value).toBe(true);

            stopWatchingResource();
            expect(isWatchingResource.value).toBe(false);
        });
    });

    describe("polling intervals", () => {
        it("should use default short polling interval (3000ms) when app is active", async () => {
            const { startWatchingResource } = useResourceWatcher(mockWatchHandler);

            startWatchingResource();
            await flushPromises();
            expect(mockWatchHandler).toHaveBeenCalledTimes(1);

            // Advance time by the default short polling interval
            jest.advanceTimersByTime(3000);
            await flushPromises();

            expect(mockWatchHandler).toHaveBeenCalledTimes(2);

            // Advance time again
            jest.advanceTimersByTime(3000);
            await flushPromises();

            expect(mockWatchHandler).toHaveBeenCalledTimes(3);
        });

        it("should use custom short polling interval when provided", async () => {
            const customOptions: WatchOptions = {
                shortPollingInterval: 1500,
            };
            const { startWatchingResource } = useResourceWatcher(mockWatchHandler, customOptions);

            startWatchingResource();
            await flushPromises();
            expect(mockWatchHandler).toHaveBeenCalledTimes(1);

            // Advance time by the custom short polling interval
            jest.advanceTimersByTime(1500);
            await flushPromises();

            expect(mockWatchHandler).toHaveBeenCalledTimes(2);
        });

        it("should switch to long polling interval when app becomes hidden", async () => {
            const { startWatchingResource } = useResourceWatcher(mockWatchHandler);

            startWatchingResource();
            await flushPromises();
            expect(mockWatchHandler).toHaveBeenCalledTimes(1);

            // Simulate visibility change event setup
            expect(mockAddEventListener).toHaveBeenCalledWith("visibilitychange", expect.any(Function));
            const visibilityChangeHandler = getVisibilityChangeHandler();

            // Change document visibility to hidden
            mockDocument.visibilityState = "hidden";
            visibilityChangeHandler();

            // The current timer (with short interval) should still complete first
            jest.advanceTimersByTime(3000);
            await flushPromises();
            expect(mockWatchHandler).toHaveBeenCalledTimes(2);

            // Now the next timer should use the long polling interval
            jest.advanceTimersByTime(10000); // Default long interval
            await flushPromises();
            expect(mockWatchHandler).toHaveBeenCalledTimes(3);
        });

        it("should use custom long polling interval when app is hidden", async () => {
            const customOptions: WatchOptions = {
                longPollingInterval: 5000,
            };
            const { startWatchingResource } = useResourceWatcher(mockWatchHandler, customOptions);

            startWatchingResource();
            await flushPromises();
            expect(mockWatchHandler).toHaveBeenCalledTimes(1);

            // Get the visibility change handler
            const visibilityChangeHandler = getVisibilityChangeHandler();

            // Change document visibility to hidden
            mockDocument.visibilityState = "hidden";
            visibilityChangeHandler();

            // Current timer (short interval) completes first
            jest.advanceTimersByTime(3000);
            await flushPromises();
            expect(mockWatchHandler).toHaveBeenCalledTimes(2);

            // Fast-forward by custom long interval
            jest.advanceTimersByTime(5000);
            await flushPromises();

            expect(mockWatchHandler).toHaveBeenCalledTimes(3);
        });

        it("should disable background polling when enableBackgroundPolling is false", async () => {
            const customOptions: WatchOptions = {
                enableBackgroundPolling: false,
            };
            const { startWatchingResource } = useResourceWatcher(mockWatchHandler, customOptions);

            startWatchingResource();
            expect(mockWatchHandler).toHaveBeenCalledTimes(1);

            // Get the visibility change handler
            const visibilityChangeHandler = getVisibilityChangeHandler();

            // Change document visibility to hidden
            mockDocument.visibilityState = "hidden";
            visibilityChangeHandler();

            // Fast-forward by any amount of time
            jest.advanceTimersByTime(30000);
            await flushPromises();

            // Should not have been called again
            expect(mockWatchHandler).toHaveBeenCalledTimes(1);
        });
    });

    describe("visibility change handling", () => {
        it("should set up visibility change listener only once", () => {
            useResourceWatcher(mockWatchHandler);
            useResourceWatcher(mockWatchHandler);

            // Should only set up listener once per instance
            expect(mockAddEventListener).toHaveBeenCalledTimes(2);
            expect(mockAddEventListener).toHaveBeenCalledWith("visibilitychange", expect.any(Function));
        });

        it("should switch to short interval when app becomes visible without restarting watcher", async () => {
            const { startWatchingResource } = useResourceWatcher(mockWatchHandler);

            startWatchingResource();
            await flushPromises();
            expect(mockWatchHandler).toHaveBeenCalledTimes(1);

            // Get the visibility change handler
            const visibilityChangeHandler = getVisibilityChangeHandler();

            // Simulate app becoming hidden
            mockDocument.visibilityState = "hidden";
            visibilityChangeHandler();

            // Clear the handler calls
            mockWatchHandler.mockClear();

            // Simulate app becoming visible again
            mockDocument.visibilityState = "visible";
            visibilityChangeHandler();

            // Should NOT immediately call the handler (watcher already running, no restart)
            await flushPromises();
            expect(mockWatchHandler).toHaveBeenCalledTimes(0);

            // But should continue with short polling interval on next scheduled poll
            jest.advanceTimersByTime(3000);
            await flushPromises();

            expect(mockWatchHandler).toHaveBeenCalledTimes(1);
        });
    });

    describe("error handling", () => {
        it("should handle errors in watch handler gracefully and continue polling", async () => {
            const consoleWarnSpy = jest.spyOn(console, "warn").mockImplementation(() => {});
            const error = new Error("Network error");
            mockWatchHandler.mockRejectedValueOnce(error).mockResolvedValue(undefined);

            const { startWatchingResource } = useResourceWatcher(mockWatchHandler);

            startWatchingResource();
            await flushPromises();

            expect(consoleWarnSpy).toHaveBeenCalledWith(error);
            expect(mockWatchHandler).toHaveBeenCalledTimes(1);

            // Should continue polling despite the error
            jest.advanceTimersByTime(3000);
            await flushPromises();

            expect(mockWatchHandler).toHaveBeenCalledTimes(2);

            consoleWarnSpy.mockRestore();
        });

        it("should handle multiple consecutive errors", async () => {
            const consoleWarnSpy = jest.spyOn(console, "warn").mockImplementation(() => {});
            const error1 = new Error("First error");
            const error2 = new Error("Second error");

            mockWatchHandler.mockRejectedValueOnce(error1).mockRejectedValueOnce(error2).mockResolvedValue(undefined);

            const { startWatchingResource } = useResourceWatcher(mockWatchHandler);

            startWatchingResource();
            await flushPromises();

            expect(consoleWarnSpy).toHaveBeenCalledWith(error1);

            jest.advanceTimersByTime(3000);
            await flushPromises();

            expect(consoleWarnSpy).toHaveBeenCalledWith(error2);

            jest.advanceTimersByTime(3000);
            await flushPromises();

            expect(mockWatchHandler).toHaveBeenCalledTimes(3);

            consoleWarnSpy.mockRestore();
        });
    });

    describe("cleanup and resource management", () => {
        it("should clear existing timeout when starting watching again", async () => {
            const { startWatchingResource } = useResourceWatcher(mockWatchHandler);

            // Start watching
            startWatchingResource();
            await flushPromises();
            expect(mockWatchHandler).toHaveBeenCalledTimes(1);

            // Start watching again before the first timeout fires
            startWatchingResource();
            await flushPromises();
            expect(mockWatchHandler).toHaveBeenCalledTimes(2);

            // Fast-forward time - should only fire once more (from the second start)
            jest.advanceTimersByTime(3000);
            await flushPromises();

            expect(mockWatchHandler).toHaveBeenCalledTimes(3);
        });

        it("should stop polling even when watch handler takes longer than interval", async () => {
            // Create a handler that takes 5 seconds to complete (longer than 3s interval)
            const slowHandler = jest.fn<WatchResourceHandler>().mockImplementation(async () => {
                // Simulate a slow network request that takes longer than the polling interval
                await new Promise((resolve) => setTimeout(resolve, 5000));
            });

            const { startWatchingResource, stopWatchingResource } = useResourceWatcher(slowHandler);

            // Start watching
            startWatchingResource();
            expect(slowHandler).toHaveBeenCalledTimes(1);

            // Advance time by 2 seconds (handler still running)
            jest.advanceTimersByTime(2000);
            await flushPromises();

            // Stop watching while the handler is still executing
            stopWatchingResource();

            // Complete the slow handler execution
            jest.advanceTimersByTime(3000); // Total 5 seconds for handler to complete
            await flushPromises();

            // Advance time well beyond the polling interval
            jest.advanceTimersByTime(10000);
            await flushPromises();

            expect(slowHandler).toHaveBeenCalledTimes(1);
        });

        it("should handle multiple overlapping slow handlers correctly", async () => {
            const slowHandler = jest.fn<WatchResourceHandler>().mockImplementation(async () => {
                await new Promise((resolve) => setTimeout(resolve, 8000)); // 8 seconds (longer than 2 intervals)
            });

            const { startWatchingResource, stopWatchingResource } = useResourceWatcher(slowHandler);

            startWatchingResource();
            expect(slowHandler).toHaveBeenCalledTimes(1);

            // Let the first handler run for 3 seconds (still running)
            jest.advanceTimersByTime(3000);
            await flushPromises();

            // The 3-second interval timer should NOT fire a new handler yet because the first is still running
            expect(slowHandler).toHaveBeenCalledTimes(1);

            // Stop watching while first handler is still running
            stopWatchingResource();

            // Complete the first handler (8 seconds total)
            jest.advanceTimersByTime(5000);
            await flushPromises();

            // Advance time, which should not trigger another call
            jest.advanceTimersByTime(3000);
            await flushPromises();

            expect(slowHandler).toHaveBeenCalledTimes(1);
        });

        it("should update isWatchingResource flag correctly with slow handlers", async () => {
            const slowHandler = jest.fn<WatchResourceHandler>().mockImplementation(async () => {
                await new Promise((resolve) => setTimeout(resolve, 5000));
            });

            const { startWatchingResource, stopWatchingResource, isWatchingResource } = useResourceWatcher(slowHandler);

            // Start watching
            startWatchingResource();
            expect(isWatchingResource.value).toBe(true);

            // Still watching while handler is running
            jest.advanceTimersByTime(2000);
            await flushPromises();
            expect(isWatchingResource.value).toBe(true);

            // Stop watching while handler is still running
            stopWatchingResource();
            expect(isWatchingResource.value).toBe(false);

            // Should remain stopped even after handler completes
            jest.advanceTimersByTime(10000);
            await flushPromises();
            expect(isWatchingResource.value).toBe(false);
        });

        it("should not schedule new timeout if current polling interval is undefined", async () => {
            const customOptions: WatchOptions = {
                enableBackgroundPolling: false,
            };
            const { startWatchingResource } = useResourceWatcher(mockWatchHandler, customOptions);

            startWatchingResource();

            // Get the visibility change handler
            const visibilityChangeHandler = getVisibilityChangeHandler();

            // Change to hidden (disables polling)
            mockDocument.visibilityState = "hidden";
            visibilityChangeHandler();

            // Clear previous calls
            mockWatchHandler.mockClear();

            // Fast-forward time significantly
            jest.advanceTimersByTime(60000);
            await flushPromises();

            // Should not have been called
            expect(mockWatchHandler).not.toHaveBeenCalled();
        });
    });

    describe("integration scenarios", () => {
        it("should work correctly with all custom options", async () => {
            const customOptions: WatchOptions = {
                shortPollingInterval: 1000,
                longPollingInterval: 4000,
                enableBackgroundPolling: true,
            };
            const { startWatchingResource } = useResourceWatcher(mockWatchHandler, customOptions);

            startWatchingResource();
            await flushPromises();
            expect(mockWatchHandler).toHaveBeenCalledTimes(1);

            // Test short interval
            jest.advanceTimersByTime(1000);
            await flushPromises();
            expect(mockWatchHandler).toHaveBeenCalledTimes(2);

            // Change to hidden
            const visibilityChangeHandler = getVisibilityChangeHandler();
            mockDocument.visibilityState = "hidden";
            visibilityChangeHandler();

            // Test long interval (after current short interval timer completes)
            jest.advanceTimersByTime(1000); // Complete current timer
            await flushPromises();
            expect(mockWatchHandler).toHaveBeenCalledTimes(3);

            jest.advanceTimersByTime(4000); // Long interval
            await flushPromises();
            expect(mockWatchHandler).toHaveBeenCalledTimes(4);
        });

        it("should handle rapid visibility state changes", async () => {
            const { startWatchingResource } = useResourceWatcher(mockWatchHandler);

            startWatchingResource();
            await flushPromises();
            expect(mockWatchHandler).toHaveBeenCalledTimes(1); // Initial call

            const visibilityChangeHandler = getVisibilityChangeHandler();

            // Change to hidden - this changes currentPollingInterval but doesn't restart timer
            mockDocument.visibilityState = "hidden";
            visibilityChangeHandler();

            // Change to visible - this changes currentPollingInterval back to short but doesn't restart
            mockDocument.visibilityState = "visible";
            visibilityChangeHandler();
            await flushPromises();
            expect(mockWatchHandler).toHaveBeenCalledTimes(1); // No additional call from becoming visible

            // The timer continues with the short interval
            jest.advanceTimersByTime(3000);
            await flushPromises();
            expect(mockWatchHandler).toHaveBeenCalledTimes(2); // + 1 from short interval timer

            // Change to hidden again
            mockDocument.visibilityState = "hidden";
            visibilityChangeHandler();

            // The next timer should use the long interval
            jest.advanceTimersByTime(10000);
            await flushPromises();
            expect(mockWatchHandler).toHaveBeenCalledTimes(3); // + 1 from long interval timer
        });
    });
});

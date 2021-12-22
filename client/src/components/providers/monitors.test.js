import { of } from "rxjs";
import { ObserverSpy } from "@hirez_io/observer-spy";
import { loadHistoryContents } from "components/providers/History/caching";
import { monitorHistoryUntilTrue, invocationStepMonitor } from "./monitors";
import * as fetch from "./fetch";

jest.mock("components/providers/History/caching");

describe("invocationStepMonitor", () => {
    let monitor$;
    let spy;
    let fetchInvocationMock;
    const invocationId = 1;
    const invocationStepDataNew = { jobs: [{ state: "new" }], state: "scheduled" };
    const invocationStepDataRunning = { jobs: [{ state: "running" }], state: "scheduled" };
    const invocationStepDataOk = { jobs: [{ state: "ok" }], state: "scheduled" };

    beforeEach(async () => {
        fetchInvocationMock = jest.spyOn(fetch, "fetchInvocationStepById");
        spy = new ObserverSpy();
    });

    test("invocationStepMonitor runs until step and job are terminal", async () => {
        // mocks fetchInvocationStep in initialFetch$
        fetchInvocationMock.mockImplementationOnce(() => () => of(invocationStepDataNew));
        // mocks fetchInvocationStep in pollingFetch$
        fetchInvocationMock.mockImplementationOnce(
            () => () => of(invocationStepDataRunning, invocationStepDataOk, invocationStepDataOk)
        );
        monitor$ = of(invocationId).pipe(invocationStepMonitor(20));
        monitor$.subscribe(spy);
        await spy.onComplete();
        expect(spy.getValues()).toEqual([invocationStepDataNew, invocationStepDataRunning, invocationStepDataOk]);
    });
    test("invocationStepMonitor terminates immediately if step is terminal", async () => {
        fetchInvocationMock.mockImplementationOnce(() => () => of(invocationStepDataOk));
        fetchInvocationMock.mockImplementationOnce(
            () => () => of(invocationStepDataRunning, invocationStepDataOk, invocationStepDataOk, invocationStepDataOk)
        );
        monitor$ = of(invocationId).pipe(invocationStepMonitor(20));
        monitor$.subscribe(spy);
        await spy.onComplete();
        expect(spy.getValues()).toEqual([invocationStepDataOk]);
    });
});

// prettier-ignore
describe("monitorHistoryUntilTrue", () => {
    let monitor$;
    let spy;
    const historyId = 1;
    let stopMonitor;
    const stopFn = () => stopMonitor == true;
    let mockLoadHistoryContent;
    let completed;

    beforeEach(async () => {
        stopMonitor = false;
        completed = false;
        mockLoadHistoryContent = of(1, 2, 3);
        loadHistoryContents.mockImplementation(() => () => mockLoadHistoryContent);
        monitor$ = monitorHistoryUntilTrue(stopFn, historyId, 20);
    });

    test("that history subscription runs until condition is met, and then once more", async () => {
        // spy on output of observable;
        spy = new ObserverSpy();
        monitor$.subscribe(spy);
        monitor$.subscribe({
            next: (val) => {
                // stop once we reach 2
                if (val >= 2) {
                    stopMonitor = true;
                }
            },
            complete: () => {
                completed = true;
            }
        })
        await spy.onComplete();

        // We stop at 2, and then take one more value.
        expect(spy.getValues()).toEqual([1, 2, 1]);
        expect(completed).toBeTruthy();
    });
});

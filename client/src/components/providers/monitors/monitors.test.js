import { of } from "rxjs";
import { ObserverSpy } from "@hirez_io/observer-spy";
import { invocationStepMonitor } from "./monitors";
import * as fetch from "../fetch";

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

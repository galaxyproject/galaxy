import { of } from "rxjs";
import { ObserverSpy } from "@hirez_io/observer-spy";
import * as caching from "components/History/caching/loadHistoryContents";
import { wipeDatabase } from "components/History/caching/db/wipeDatabase";
import { monitorHistoryUntilTrue } from "./monitors";

jest.mock("../../History/caching");

afterEach(async () => await wipeDatabase());

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
        jest.spyOn(caching, 'loadHistoryContents').mockImplementation(() => () => mockLoadHistoryContent);
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
        // wait for monitor to run out
        await spy.onComplete();

        // We stop at 2, and then take one more value.
        expect(spy.getValues()).toEqual([1, 2, 1]);
        expect(completed).toBeTruthy();
    });
});

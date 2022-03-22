import { of } from "rxjs";
import { ObserverSpy } from "@hirez_io/observer-spy";

import { singleton } from "./singleton";

describe("creating observable singleton", () => {
    const source = { id: "a" };
    const source$ = of(source);

    // give one source observable get one product out
    // each time the observable is subscribed to
    test("same input should return the exact same output even from different observable streams", () => {
        // build unique products with factory
        const factory = jest.fn((db) => {
            return { id: Math.random() };
        });

        const productA$ = source$.pipe(singleton(factory));

        const productA2$ = source$.pipe(singleton(factory));

        const spyA = new ObserverSpy();
        productA$.subscribe(spyA);

        const spyA2 = new ObserverSpy();
        productA2$.subscribe(spyA2);

        expect(spyA.getFirstValue()).toBe(spyA2.getFirstValue());
        expect(factory).toHaveBeenCalledTimes(1);
    });
});

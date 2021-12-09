import { of, timer } from "rxjs";
import { takeUntil } from "rxjs/operators";
import { ObserverSpy } from "@hirez_io/observer-spy";
import { wait } from "jest/helpers";
import { wipeDatabase } from "./wipeDatabase";

import { monitorQuery } from "./monitorQuery";
import { content$, dscContent$ } from "./observables";
import { cacheContent, cacheCollectionContent, bulkCacheContent, bulkCacheDscContent } from "./promises";

// test data
import historyContent from "components/providers/History/test/json/historyContent.json";
import collectionContent from "components/providers/History/test/json/collectionContent.json";

jest.mock("app");
jest.mock("../../caching");

const monitorSpinUp = 100;
const monitorSafetyTimeout = 800;

const pluckAll = (arr, prop) => arr.map((o) => o[prop]);

afterEach(wipeDatabase);

// prettier-ignore
describe("monitorQuery: history content", () => {

    describe("initial results", () => {
        test("first monitor event has initial results reflecting existing matches in db", async () => {
            const cachedContent = await bulkCacheContent(historyContent, true);
            const cachedContentIds = new Set(pluckAll(cachedContent, "_id"));

            // create new monitor with query selector hid > 160
            const cutoffHid = 120;
            const selector = { hid: { $gt: cutoffHid } };
            const monitor$ = of({ selector }).pipe(
                monitorQuery({ db$: content$ }),
                takeUntil(timer(monitorSafetyTimeout)),
            );

            // // listen to observable, wait for complete
            const spy = new ObserverSpy();
            monitor$.subscribe(spy);
            await spy.onComplete();

            // should get one emit out with just the intial matches
            const emits = spy.getValues();
            expect(spy.getValuesLength()).toBeGreaterThan(0);
            expect(spy.getValuesLength()).toBeLessThanOrEqual(cachedContentIds.size);
            emits.forEach(({ doc, match, initial }) => {
                // we aren't changing anything, results should be initial matches
                expect(match).toBeTruthy();
                // initial results have an identifying flag
                expect(initial).toBe(true);
                // every doc should match the selector
                expect(doc => doc.hid > cutoffHid).toBeTruthy();
                // every doc should be in the initially cached items
                expect(cachedContentIds.has(doc._id)).toBeTruthy();
            });
        });
    });

    describe("updates", () => {

        test("INSERT: adding to cache after instantiation should emit a new doc", async () => {

            const cutoffHid = 50;
            const selector = { hid: { $gt: cutoffHid } };
            const monitor$ = of({ selector }).pipe(
                monitorQuery({ db$: content$ }),
                takeUntil(timer(monitorSafetyTimeout)),
            );

            const spy = new ObserverSpy();
            monitor$.subscribe(spy);
            
            // wait for the monitor to spin-up so the insert doesn't look like the initial vals
            await wait(monitorSpinUp);

            // Insert a row, make sure it should match the selector
            const insertedContent = await cacheContent(historyContent[0], true);
            expect(insertedContent.hid > cutoffHid).toBeTruthy();

            // wait for observable end
            await spy.onComplete();

            const emits = spy.getValues();
            expect(spy.getValuesLength()).toEqual(1);
            emits.forEach(({ doc, match, initial, update }) => {
                expect(doc.hid > cutoffHid).toBeTruthy();
                expect(match).toBe(true);
                expect(initial).toBeUndefined();
                expect(update).toBe(true);
            })
        });

        test("UPDATE: updating a previously emitted doc should emit an update event", async () => {
            const cutoffHid = 50;

            // Insert a row, make sure it should match the selector
            const insertedContent = await cacheContent(historyContent[0], true);
            expect(insertedContent.hid > cutoffHid).toBeTruthy();

            // subscribe to listener
            const selector = { hid: { $gt: cutoffHid } };
            const monitor$ = of({ selector }).pipe(
                monitorQuery({ db$: content$ }),
                takeUntil(timer(monitorSafetyTimeout)),
            );
            const spy = new ObserverSpy();
            monitor$.subscribe(spy);
            
            // wait for the monitor to spin-up so the insert doesn't look like the initial vals
            await wait(monitorSpinUp);

            // update the content
            const fooVal = 123;
            insertedContent.foo = fooVal;
            const updatedContent = await cacheContent(insertedContent, true);
            expect(updatedContent._id).toEqual(insertedContent._id);
            expect(updatedContent.foo).toEqual(fooVal);

            // wait for observable end
            await spy.onComplete();
            expect(spy.getValuesLength()).toEqual(2); // initial insert + later update

            // check first event
            const firstEvent = spy.getValueAt(0);
            {
                const { doc, match, initial, update } = firstEvent;
                expect(doc.foo).toBeUndefined();
                expect(match).toBe(true);
                expect(initial).toBe(true);
                expect(update).toBeUndefined();
            }

            // check update event
            const secondEvent = spy.getValueAt(1);
            {
                const { doc, match, initial, update } = secondEvent;
                expect(doc.foo).toBe(fooVal);
                expect(match).toBe(true);
                expect(initial).toBeUndefined();
                expect(update).toBe(true);
            }
        });

        test("DELETE: cache update causes element to no longer be in selection", async () => {
            const cutoffHid = 50;

            // Insert a row, make sure it should match the selector
            const insertedContent = await cacheContent(historyContent[0], true);
            expect(insertedContent.hid > cutoffHid).toBeTruthy();

            // subscribe to listener
            const selector = { hid: { $gt: cutoffHid } };
            const monitor$ = of({ selector }).pipe(
                monitorQuery({ db$: content$ }),
                takeUntil(timer(monitorSafetyTimeout)),
            );
            const spy = new ObserverSpy();
            monitor$.subscribe(spy);
            
            // wait for the monitor to spin-up so the insert doesn't look like the initial vals
            await wait(monitorSpinUp);

            // update the content to be outside the selector
            const badHid = -10000;
            insertedContent.hid = badHid; // no longer > cutoffHid
            const updatedContent = await cacheContent(insertedContent, true);
            expect(updatedContent._id).toEqual(insertedContent._id);
            expect(updatedContent.hid).toEqual(badHid);

            // wait for observable end
            await spy.onComplete();
            expect(spy.getValuesLength()).toEqual(2); // initial insert + later update

            // check first event
            const firstEvent = spy.getValueAt(0);
            {
                const { doc, match, initial, update } = firstEvent;
                expect(doc).toBeDefined();
                expect(doc).toBeInstanceOf(Object);
                expect(doc.hid).not.toEqual(badHid);
                expect(match).toBe(true);
                expect(initial).toBe(true);
                expect(update).toBeUndefined();
            }

            // check update event
            const secondEvent = spy.getValueAt(1);
            {
                const { doc, match, initial, update } = secondEvent;
                expect(doc).toBeDefined();
                expect(doc).toBeInstanceOf(Object);
                expect(doc.hid).toEqual(badHid);
                expect(match).toBe(false); // no longer matches selector
                expect(initial).toBeUndefined();
                expect(update).toBe(true);
            }
        });
    });
});

describe("monitorQuery: collection content", () => {
    // doctor and cache sample content
    const fakeParentUrl = "/abc/def/ghi";
    const testContent = collectionContent.map((doc) => {
        doc.parent_url = fakeParentUrl;
        return doc;
    });

    describe("initial results", () => {
        test("first monitor event has initial results reflecting existing matches in db", async () => {
            // insert some stuff
            const cachedDscContent = await bulkCacheDscContent(testContent, true);
            const cachedContentIds = new Set(pluckAll(cachedDscContent, "_id"));

            // create new monitor
            const limitIndex = 1;
            const selector = {
                parent_url: fakeParentUrl,
                element_index: { $gt: limitIndex },
            };
            const monitor$ = of({ selector }).pipe(
                monitorQuery({ db$: dscContent$ }),
                takeUntil(timer(monitorSafetyTimeout))
            );

            // wait til done
            const spy = new ObserverSpy();
            monitor$.subscribe(spy);
            await spy.onComplete();

            // check emits
            const emits = spy.getValues();
            expect(spy.getValuesLength()).toBeGreaterThan(0);
            expect(spy.getValuesLength()).toBeLessThanOrEqual(cachedContentIds.size);
            emits.forEach(({ doc, match, initial, update }) => {
                expect(match).toBe(true);
                expect(initial).toBe(true);
                expect(update).toBeUndefined();
                expect(cachedContentIds.has(doc._id)).toBeTruthy();
                expect(doc.element_index > limitIndex).toBeTruthy();
                expect(doc.parent_url).toEqual(fakeParentUrl);
            });
        });
    });

    describe("updates", () => {
        test("INSERT: adding to cache after instantiation should emit a new doc", async () => {
            // createa  monitor
            const limitIndex = 0;
            const selector = {
                parent_url: fakeParentUrl,
                element_index: { $gt: limitIndex },
            };
            const monitor$ = of({ selector }).pipe(
                monitorQuery({ db$: dscContent$ }),
                takeUntil(timer(monitorSafetyTimeout))
            );

            const spy = new ObserverSpy();
            monitor$.subscribe(spy);

            // wait for the monitor to spin-up so the insert doesn't look like the initial vals
            await wait(monitorSpinUp);

            // Insert a row, make sure it should match the selector
            const insertedContent = await cacheCollectionContent(testContent[3], true);
            expect(insertedContent.element_index > limitIndex).toBeTruthy();

            // wait for observable end
            await spy.onComplete();

            const emits = spy.getValues();
            expect(spy.getValuesLength()).toEqual(1);
            emits.forEach(({ doc, match, initial, update }) => {
                expect(doc.element_index > limitIndex).toBeTruthy();
                expect(doc._id).toEqual(insertedContent._id);
                expect(match).toBe(true);
                expect(initial).toBeUndefined();
                expect(update).toBe(true);
            });
        });

        test("UPDATE: updating a previously emitted doc should emit an update event", async () => {
            const limitIndex = 0;

            // Insert a row, make sure it should match the selector
            const insertedContent = await cacheCollectionContent(testContent[1], true);
            expect(insertedContent.element_index > limitIndex).toBeTruthy();

            // create  monitor
            const selector = {
                parent_url: fakeParentUrl,
                element_index: { $gt: limitIndex },
            };
            const monitor$ = of({ selector }).pipe(
                monitorQuery({ db$: dscContent$ }),
                takeUntil(timer(monitorSafetyTimeout))
            );

            const spy = new ObserverSpy();
            monitor$.subscribe(spy);

            // wait for the monitor to spin-up so the insert doesn't look like the initial vals
            await wait(monitorSpinUp);

            // update the content
            const fooVal = 123;
            insertedContent.foo = fooVal;
            const updatedContent = await cacheCollectionContent(insertedContent, true);
            expect(updatedContent._id).toEqual(insertedContent._id);
            expect(updatedContent.foo).toEqual(fooVal);

            // wait for observable end
            await spy.onComplete();
            expect(spy.getValuesLength()).toEqual(2); // initial insert + later update

            // check first event
            const firstEvent = spy.getValueAt(0);
            {
                const { doc, match, initial, update } = firstEvent;
                expect(doc.foo).toBeUndefined();
                expect(match).toBe(true);
                expect(initial).toBe(true);
                expect(update).toBeUndefined();
            }

            // check update event
            const secondEvent = spy.getValueAt(1);
            {
                const { doc, match, initial, update } = secondEvent;
                expect(doc.foo).toBe(fooVal);
                expect(match).toBe(true);
                expect(initial).toBeUndefined();
                expect(update).toBe(true);
            }
        });

        test("DELETE: cache update causes element to no longer be in selection", async () => {
            const limitIndex = 0;

            // Insert a row, make sure it should match the selector
            const insertedContent = await cacheCollectionContent(testContent[1], true);
            expect(insertedContent.element_index > limitIndex).toBeTruthy();

            // create  monitor
            const selector = {
                parent_url: fakeParentUrl,
                element_index: { $gt: limitIndex },
            };
            const monitor$ = of({ selector }).pipe(
                monitorQuery({ db$: dscContent$ }),
                takeUntil(timer(monitorSafetyTimeout))
            );

            const spy = new ObserverSpy();
            monitor$.subscribe(spy);

            // update the content to be outside the selector
            const badIndex = -10000;
            insertedContent.element_index = badIndex; // no longer > cutoffHid
            const updatedContent = await cacheCollectionContent(insertedContent, true);
            expect(updatedContent._id).toEqual(insertedContent._id);
            expect(updatedContent.element_index).toEqual(badIndex);

            // wait for observable end
            await spy.onComplete();
            expect(spy.getValuesLength()).toEqual(2); // initial insert + later update

            // check first event
            const firstEvent = spy.getValueAt(0);
            {
                const { doc, match, initial, update } = firstEvent;
                expect(doc).toBeDefined();
                expect(doc).toBeInstanceOf(Object);
                expect(doc.element_index).not.toEqual(badIndex);
                expect(match).toBe(true);
                expect(initial).toBe(true);
                expect(update).toBeUndefined();
            }

            // check update event
            const secondEvent = spy.getValueAt(1);
            {
                const { doc, match, initial, update } = secondEvent;
                expect(doc).toBeDefined();
                expect(doc).toBeInstanceOf(Object);
                expect(doc.element_index).toEqual(badIndex);
                expect(match).toBe(false); // no longer matches selector
                expect(initial).toBeUndefined();
                expect(update).toBe(true);
            }
        });
    });
});

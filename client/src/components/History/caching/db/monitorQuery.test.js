import { of, timer } from "rxjs";
import { take, takeUntil } from "rxjs/operators";
import { ObserverSpy } from "@hirez_io/observer-spy";
import { wait } from "jest/helpers";
import { wipeDatabase } from "./wipeDatabase";

import { monitorQuery, ACTIONS } from "./monitorQuery";
import { content$, dscContent$ } from "./observables";
import {
    cacheContent,
    getCachedContent,
    bulkCacheContent,
    bulkCacheDscContent,
    cacheCollectionContent,
    getCachedCollectionContent,
} from "./promises";

// test data
import historyContent from "../../test/json/historyContent.json";
import collectionContent from "../../test/json/collectionContent.json";

const monitorSpinUp = 100;

afterEach(async () => await wipeDatabase());

// prettier-ignore
describe("monitorQuery: history content", () => {
    describe("initial results", () => {
        const selector = { hid: { $gt: 160 } };

        let monitor$;
        let spy;

        beforeEach(async () => {
            // create monitor with query selector hid > 160
            monitor$ = of({ selector }).pipe(
                monitorQuery({ db$: content$ }),
                take(1),
                takeUntil(timer(2000)), // safeguard
            );

            // insert content
            await bulkCacheContent(historyContent);

            // spy on output of observable;
            spy = new ObserverSpy();
            monitor$.subscribe(spy);

            // wait for monitor to spin-up
            await wait(monitorSpinUp);
        });

        test("first monitor event has initial results reflecting existing matches in db", async () => {
            // wait for monitor to run out
            await spy.onComplete();

            // check initial matches
            const { initialMatches } = spy.getFirstValue();
            expect(initialMatches).toBeDefined();
            expect(initialMatches.length).toBeGreaterThan(0);
            initialMatches.forEach((doc) => {
                expect(doc.hid).toBeGreaterThan(selector.hid.$gt);
            });
        });
    });

    describe("updates", () => {
        const selector = { hid: { $gt: 160 } };

        let monitor$;
        let spy;
        let insertResults;

        beforeEach(async () => {
            monitor$ = of({ selector }).pipe(
                monitorQuery({ db$: content$ }),
                take(2),
                takeUntil(timer(2000)), // safeguard
            );

            // insert content
            insertResults = await bulkCacheContent(historyContent);

            // spy on output of observable;
            spy = new ObserverSpy();
            monitor$.subscribe(spy);

            // wait for monitor to spin-up
            await wait(monitorSpinUp);
        });

        test("new insert matching selector should emit an ADD", async () => {
            // copy document, insert copy with some new props
            const id = insertResults[0].id;
            // eslint-disable-next-line no-unused-vars
            const { _id, _rev, ...newDoc } = await getCachedContent(id);
            newDoc.hid = 10000;
            newDoc.id = "234234234";
            const cacheUpdate = await cacheContent(newDoc);
            expect(cacheUpdate.updated).toBeTruthy();

            // wait for monitor to run out
            await spy.onComplete();

            // look for initial matches
            const { initialMatches } = spy.getFirstValue();
            expect(initialMatches).toBeDefined();
            expect(initialMatches.length).toBeGreaterThan(0);

            // make sure the updated element is NOT in the initial matches
            const inInitialSet = initialMatches.filter((doc) => doc._id == cacheUpdate.id);
            expect(inInitialSet.length).toEqual(0);

            // check for add event
            const { action, doc } = spy.getLastValue();
            expect(action).toBeDefined();
            expect(doc).toBeDefined();
            expect(action).toEqual(ACTIONS.ADD);
            expect(doc.hid).toEqual(newDoc.hid);
        });

        test("update still covered by selector should emit an UPDATE", async () => {
            // update existing doc
            const id = insertResults[0].id;
            const testDoc = await getCachedContent(id);
            testDoc.foo = 123;
            const cacheUpdate = await cacheContent(testDoc);
            expect(cacheUpdate.updated).toBeTruthy();

            // wait for monitor to run out
            await spy.onComplete();

            // look for initial matches
            const { initialMatches } = spy.getFirstValue();
            expect(initialMatches).toBeDefined();
            expect(initialMatches.length).toBeGreaterThan(0);

            // make sure the updated element is in the initial matches
            const inInitialSet = initialMatches.filter((doc) => doc._id == cacheUpdate.id);
            expect(inInitialSet.length).toEqual(1);

            // check for update event
            const { action, doc } = spy.getLastValue();
            expect(action).toBeDefined();
            expect(doc).toBeDefined();
            expect(action).toEqual(ACTIONS.UPDATE);
            expect(doc.foo).toEqual(testDoc.foo);
        });

        test("update no longer covered by selector should emit a REMOVE", async () => {
            // update doc to be outside query
            const id = insertResults[0].id;
            const testDoc = await getCachedContent(id);
            testDoc.hid = -3000;
            const cacheUpdate = await cacheContent(testDoc);
            expect(cacheUpdate.updated).toBeTruthy();

            // wait for monitor to run out
            await spy.onComplete();

            // look for initial matches
            const { initialMatches } = spy.getFirstValue();
            expect(initialMatches).toBeDefined();
            expect(initialMatches.length).toBeGreaterThan(0);

            // make sure the updated element is in the initial matches
            const inInitialSet = initialMatches.filter((doc) => doc._id == cacheUpdate.id);
            expect(inInitialSet.length).toEqual(1);

            // check for remove event
            const { action, doc } = spy.getLastValue();
            expect(action).toBeDefined();
            expect(doc).toBeDefined();
            expect(action).toEqual(ACTIONS.REMOVE);
            expect(doc.hid).toEqual(testDoc.hid);
        });
    });
});

describe("monitorQuery: collection content", () => {
    // pre-process raw collection content
    const fakeParentUrl = "/abc/def/ghi";
    const testContent = collectionContent.map((doc) => {
        doc.parent_url = fakeParentUrl;
        return doc;
    });

    describe("initial results", () => {
        const selector = {
            parent_url: fakeParentUrl,
            element_index: { $gt: 1 },
        };

        let monitor$;
        let spy;

        beforeEach(async () => {
            monitor$ = of({ selector }).pipe(
                monitorQuery({ db$: dscContent$ }),
                take(1),
                takeUntil(timer(2000)) // safeguard
            );

            // insert content
            await bulkCacheDscContent(testContent);

            // spy on output of observable;
            spy = new ObserverSpy();
            monitor$.subscribe(spy);

            // wait for monitor to spin-up
            await wait(monitorSpinUp);
        });

        test("first monitor event has initial results reflecting existing matches in db", async () => {
            // wait for monitor to run out
            await spy.onComplete();

            // check initial matches
            const { initialMatches } = spy.getFirstValue();
            expect(initialMatches).toBeDefined();
            expect(initialMatches.length).toBeGreaterThan(0);
            initialMatches.forEach((doc) => {
                expect(doc.parent_url).toEqual(selector.parent_url);
                expect(doc.element_index).toBeGreaterThan(selector.element_index.$gt);
            });
        });
    });

    describe("updates", () => {
        const selector = {
            parent_url: fakeParentUrl,
            name: { $regex: /M117/i },
        };

        let monitor$;
        let insertResults;
        let spy;

        beforeEach(async () => {
            monitor$ = of({ selector }).pipe(
                monitorQuery({ db$: dscContent$ }),
                take(2),
                takeUntil(timer(2000)) // safeguard
            );
            insertResults = await bulkCacheDscContent(testContent);
            spy = new ObserverSpy();
            monitor$.subscribe(spy);

            // wait for monitor to spin-up
            await wait(monitorSpinUp);
        });

        test("new insert matching selector should emit an ADD", async () => {
            // insert copy of new doc
            const newDoc = testContent[0];
            newDoc.element_index = 10000;
            const addResult = await cacheCollectionContent(newDoc);
            expect(addResult.updated).toBeTruthy();

            // check the change is in there
            const { id: newId } = addResult;
            const lookup = await getCachedCollectionContent(newId);
            expect(lookup.element_index).toEqual(newDoc.element_index);

            // wait for monitor to run out
            await spy.onComplete();

            expect(spy.receivedNext()).toBe(true);
            expect(spy.receivedComplete()).toBe(true);
            expect(spy.getValuesLength()).toBe(2);

            // look for initial matches
            const { initialMatches } = spy.getFirstValue();
            expect(initialMatches).toBeDefined();
            expect(initialMatches.length).toBeGreaterThan(0);

            // make sure the insert element is NOT in the initial matches
            const inInitialSet = initialMatches.filter((doc) => doc._id == addResult.id);
            expect(inInitialSet.length).toEqual(0);

            // look for add event
            const { action, doc } = spy.getLastValue();
            expect(action).toBeDefined();
            expect(doc).toBeDefined();
            expect(action).toEqual(ACTIONS.ADD);
            expect(doc.element_index).toEqual(newDoc.element_index);
        });

        test("update still covered by selector should emit an UPDATE", async () => {
            // look up an existing doc
            const id = insertResults[0].id;
            const lookupDoc = await getCachedCollectionContent(id);
            expect(lookupDoc).toBeDefined();
            expect(lookupDoc._id).toEqual(id);

            // update it
            lookupDoc.foo = "fakestuff";
            const updateResult = await cacheCollectionContent(lookupDoc);
            expect(updateResult.updated).toBeTruthy();

            // wait for monitor to run out
            await spy.onComplete();

            // look for initial matches
            const { initialMatches } = spy.getFirstValue();
            expect(initialMatches).toBeDefined();
            expect(initialMatches.length).toBeGreaterThan(0);

            // make sure the updated doc is in the initial matches
            const inInitialSet = initialMatches.filter((doc) => doc._id == updateResult.id);
            expect(inInitialSet.length).toEqual(1);

            // look for add event
            const { action, doc } = spy.getLastValue();
            expect(action).toBeDefined();
            expect(doc).toBeDefined();
            expect(action).toEqual(ACTIONS.UPDATE);
            expect(doc.foo).toEqual(lookupDoc.foo);
        });

        test("update no longer covered by selector should emit a REMOVE", async () => {
            // set to deleted
            const id = insertResults[0].id;
            const testDoc = await getCachedCollectionContent(id);
            testDoc.name = "ABC";
            testDoc.element_identifier = "ABC";
            const cacheUpdate = await cacheCollectionContent(testDoc);
            expect(cacheUpdate.updated).toBeTruthy();

            // wait for monitor to run out
            await spy.onComplete();

            // look for initial matches
            const { initialMatches } = spy.getFirstValue();
            expect(initialMatches).toBeDefined();
            expect(initialMatches.length).toBeGreaterThan(0);

            // make sure the updated element is in the initial matches
            const inInitialSet = initialMatches.filter((doc) => doc._id == cacheUpdate.id);
            expect(inInitialSet.length).toEqual(1);

            // look for the remove event
            const { action, doc } = spy.getLastValue();
            expect(action).toBeDefined();
            expect(doc).toBeDefined();
            expect(action).toEqual(ACTIONS.REMOVE);
            expect(doc.name).toEqual(testDoc.name);
            expect(doc.element_identifier).toEqual(testDoc.element_identifier);
        });
    });
});

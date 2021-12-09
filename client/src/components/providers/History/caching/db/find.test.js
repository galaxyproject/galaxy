import { Subject } from "rxjs";
import { take } from "rxjs/operators";
import { ObserverSpy } from "@hirez_io/observer-spy";

import { wipeDatabase } from "./wipeDatabase";
import { bulkCacheContent, bulkCacheDscContent } from "./promises";
import { content$, dscContent$, buildContentId } from "./observables";
import { find } from "./find";

// test data
import historyContent from "components/History/test/json/historyContent.json";
import collectionContent from "components/providers/History/test/json/collectionContent.json";

beforeEach(wipeDatabase);
afterEach(wipeDatabase);

describe("find operator", () => {
    // setup request subject, find observable, and spy to look at output
    const request$ = new Subject();

    // unsub, if requred
    let obs$;
    let spy;

    describe("content database (content$) queries", () => {
        beforeEach(async () => await bulkCacheContent(historyContent));

        beforeEach(() => {
            obs$ = request$.pipe(find(content$), take(1));
            spy = new ObserverSpy();
            obs$.subscribe(spy);
        });

        test("should select everything with a blank selector", async () => {
            const request = { selector: {} };
            request$.next(request);
            await spy.onComplete();

            const results = spy.getFirstValue();
            expect(spy.receivedNext()).toBe(true);
            expect(spy.receivedComplete()).toBe(true);
            expect(results.length).toEqual(historyContent.length);
        });

        test("should return everything with a blank selector, while building a custom index", async () => {
            const request = {
                selector: {},
                sort: [{ _id: "desc" }],
                index: {
                    fields: ["_id"],
                    sort: [{ _id: "desc" }],
                    name: "foo index",
                    ddoc: "idx-foo",
                },
            };
            request$.next(request);
            await spy.onComplete();

            const results = spy.getFirstValue();
            expect(spy.receivedNext()).toBe(true);
            expect(spy.receivedComplete()).toBe(true);
            expect(results.length).toEqual(historyContent.length);
        });

        test("should return with a limit", async () => {
            const limit = 3;
            const request = {
                selector: {},
                sort: [{ _id: "desc" }],
                limit,
                index: {
                    fields: ["_id"],
                    sort: [{ _id: "desc" }],
                    name: "foo index",
                    ddoc: "idx-foo",
                },
            };
            request$.next(request);
            await spy.onComplete();

            const results = spy.getFirstValue();
            expect(spy.receivedNext()).toBe(true);
            expect(spy.receivedComplete()).toBe(true);
            expect(results.length).toEqual(limit);
        });

        test("descending history-hid query", async () => {
            const { history_id, hid } = historyContent[0];
            const request = {
                selector: {
                    _id: { $lte: `${history_id}-${hid}` },
                },
                sort: [{ _id: "desc" }],
                limit: 3,
                index: {
                    fields: ["_id"],
                    sort: [{ _id: "desc" }],
                    name: "content history_id and hid descending",
                    ddoc: "idx-historyid-hid-desc",
                },
            };
            request$.next(request);
            await spy.onComplete();

            const results = spy.getFirstValue();
            expect(spy.receivedNext()).toBe(true);
            expect(spy.receivedComplete()).toBe(true);
            expect(results.length).toEqual(3);

            results.forEach((doc) => {
                expect(doc.history_id).toEqual(history_id);
                expect(doc.hid).toBeLessThanOrEqual(hid);
            });
        });

        test("descending with visible flag", async () => {
            const { history_id, hid } = historyContent[0];
            const request = {
                selector: {
                    _id: { $lte: `${history_id}-${hid}` },
                    visible: false,
                },
                sort: [{ _id: "desc" }],
                limit: 3,
                index: {
                    fields: ["_id"],
                    sort: [{ _id: "desc" }],
                    name: "content history_id and hid descending",
                    ddoc: "idx-historyid-hid-desc",
                },
            };
            request$.next(request);
            await spy.onComplete();

            const results = spy.getFirstValue();
            expect(spy.receivedNext()).toBe(true);
            expect(spy.receivedComplete()).toBe(true);

            // only put two visible items in the test data
            const visibleRows = historyContent.filter((row) => row.visible == false);
            expect(results.length).toEqual(visibleRows.length);

            results.forEach((doc) => {
                expect(doc.history_id).toEqual(history_id);
                expect(doc.hid).toBeLessThanOrEqual(hid);
                expect(doc.visible).toEqual(false);
            });
        });

        test("descending with isDeleted flag", async () => {
            const { history_id, hid } = historyContent[0];
            const request = {
                selector: {
                    _id: { $lte: `${history_id}-${hid}` },
                    isDeleted: true,
                },
                sort: [{ _id: "desc" }],
                limit: 3,
                index: {
                    fields: ["_id"],
                    sort: [{ _id: "desc" }],
                    name: "content history_id and hid descending",
                    ddoc: "idx-historyid-hid-desc",
                },
            };
            request$.next(request);
            await spy.onComplete();

            const results = spy.getFirstValue();
            // console.log(results);
            expect(spy.receivedNext()).toBe(true);
            expect(spy.receivedComplete()).toBe(true);

            // only put two visible items in the test data
            const undeletedRows = historyContent.filter((row) => {
                return row.hid <= hid && row.deleted === true;
            });
            expect(results.length).toEqual(undeletedRows.length);

            results.forEach((doc) => {
                expect(doc.history_id).toEqual(history_id);
                expect(doc.hid).toBeLessThanOrEqual(hid);
                expect(doc.isDeleted).toEqual(true);
            });
        });

        test("ascending history-hid query", async () => {
            const doc = historyContent[5];
            const { history_id, hid } = doc;
            const targetHid = buildContentId(doc);
            const request = {
                selector: {
                    _id: { $gt: targetHid },
                },
                sort: [{ _id: "desc" }],
                limit: 3,
                index: {
                    fields: ["_id"],
                    sort: [{ _id: "desc" }],
                    name: "content history_id and hid descending",
                    ddoc: "idx-historyid-hid-desc",
                },
            };
            request$.next(request);
            await spy.onComplete();

            const results = spy.getFirstValue();
            expect(spy.receivedNext()).toBe(true);
            expect(spy.receivedComplete()).toBe(true);

            // no additional fitlers should show all undeleted and visible rows
            const expectedRows = historyContent.filter((row) => {
                return row.hid > hid && row.deleted === false && row.visible == true;
            });
            expect(results.length).toEqual(expectedRows.length);

            results.forEach((doc) => {
                expect(doc.history_id).toEqual(history_id);
                expect(doc.hid).toBeGreaterThan(hid);
            });
        });

        test("ascending with visible flag", async () => {
            // start at the 5th row and look upwards
            const doc = historyContent[5];
            const { hid } = doc;
            const targetId = buildContentId(doc);
            const request = {
                selector: {
                    _id: { $gt: targetId },
                    visible: false,
                },
                sort: [{ _id: "desc" }],
                limit: 3,
                index: {
                    fields: ["_id"],
                    sort: [{ _id: "desc" }],
                    name: "content history_id and hid descending",
                    ddoc: "idx-historyid-hid-desc",
                },
            };
            request$.next(request);
            await spy.onComplete();

            const results = spy.getFirstValue();
            expect(spy.receivedNext()).toBe(true);
            expect(spy.receivedComplete()).toBe(true);

            // count the invisible rows where the hid > targetId;
            const expectedRows = historyContent.filter((row) => {
                return row.hid > hid && row.visible === false;
            });
            expect(results.length).toEqual(expectedRows.length);
        });

        test("ascending with isDeleted flag", async () => {
            const doc = historyContent[5];
            const { history_id, hid } = doc;
            const targetId = buildContentId(doc);
            const request = {
                selector: {
                    _id: { $gt: targetId },
                    isDeleted: true,
                },
                sort: [{ _id: "desc" }],
                limit: 3,
                index: {
                    fields: ["_id"],
                    sort: [{ _id: "desc" }],
                    name: "content history_id and hid descending",
                    ddoc: "idx-historyid-hid-desc",
                },
            };
            request$.next(request);
            await spy.onComplete();

            const results = spy.getFirstValue();
            expect(spy.receivedNext()).toBe(true);
            expect(spy.receivedComplete()).toBe(true);

            // only put one deleted near the top
            const expectedRows = historyContent.filter((row) => {
                return row.hid > hid && row.deleted === true;
            });
            expect(results.length).toEqual(expectedRows.length);

            results.forEach((doc) => {
                expect(doc.history_id).toEqual(history_id);
                expect(doc.hid).toBeGreaterThan(hid);
                expect(doc.isDeleted).toEqual(true);
            });
        });
    });

    describe("collection content database (dscContent$) queries", () => {
        // put some stuff in the cache
        // preprocess the collection content
        const fakeParent = "/foo/bar";
        const dscTestContent = collectionContent.map((props) => {
            props.parent_url = fakeParent;
            return props;
        });

        beforeEach(async () => await bulkCacheDscContent(dscTestContent));

        beforeEach(() => {
            obs$ = request$.pipe(find(dscContent$), take(1));
            spy = new ObserverSpy();
            obs$.subscribe(spy);
        });

        test("should select everything with a blank selector", async () => {
            const request = { selector: {} };
            request$.next(request);
            await spy.onComplete();

            const results = spy.getFirstValue();
            expect(spy.receivedNext()).toBe(true);
            expect(spy.receivedComplete()).toBe(true);
            expect(results.length).toEqual(collectionContent.length);
        });

        test("ascending element_index", async () => {
            const request = {
                selector: {
                    _id: { $gte: `${fakeParent}-0` },
                },
                sort: [{ _id: "asc" }],
                index: {
                    fields: ["_id"],
                    sort: [{ _id: "asc" }],
                    name: "ascending index",
                    ddoc: "idx-collection-ascending",
                },
            };
            request$.next(request);
            await spy.onComplete();

            const results = spy.getFirstValue();
            expect(spy.receivedNext()).toBe(true);
            expect(spy.receivedComplete()).toBe(true);
            expect(results.length).toEqual(collectionContent.length);
        });

        test("ascending element_index with name regex", async () => {
            const request = {
                selector: {
                    _id: { $gte: `${fakeParent}-0` },
                    element_identifier: { $regex: /M117C1/i },
                },
                sort: [{ _id: "asc" }],
                index: {
                    fields: ["_id"],
                    sort: [{ _id: "asc" }],
                    name: "ascending index",
                    ddoc: "idx-collection-ascending",
                },
            };
            request$.next(request);
            await spy.onComplete();

            const results = spy.getFirstValue();
            expect(spy.receivedNext()).toBe(true);
            expect(spy.receivedComplete()).toBe(true);
            expect(results.length).toBeLessThan(collectionContent.length);
        });
    });
});

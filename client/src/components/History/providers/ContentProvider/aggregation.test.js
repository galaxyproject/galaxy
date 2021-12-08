import SkipList from "proper-skip-list";
import { buildContentResult } from "./aggregation";
import { SEEK } from "components/providers/History/caching/enums";

jest.mock("app");
jest.mock("components/providers/History/caching");

describe("buildContentResult", () => {
    describe("query history content from aggregate storage", () => {
        const updateList = new SkipList();

        // history content is keyed by hid, descending order
        const keyDirection = SEEK.DESC;
        const getKey = (item) => item.hid;
        const pageSize = 2;

        // sample content, indexed by hid
        const hids = [100, 95, 61, 60, 50, 44, 41, 17, 1].sort();
        hids.forEach((hid) => updateList.upsert(hid, { hid }));

        test("query key exists, query key in middle", () => {
            const queryKey = 60;
            const summarize = buildContentResult({ keyDirection, pageSize, getKey });

            // choose a hid we know is in the results
            const { contents, targetKey, startKey, startKeyIndex } = summarize([updateList, queryKey]);

            // returns the key we used to query the skiplist
            expect(targetKey).toEqual(queryKey);

            // the closest key to targetKey in the event that targetKey does not exist
            expect(startKey).toEqual(queryKey);

            // the array index of startKey
            expect(startKeyIndex).toEqual(2);

            // pageSize causes aggregation to back up one page from start of list, then delivers
            // the previous page, the exact match, then 2 pages after the match
            const resultKeys = contents.map(getKey);
            expect(resultKeys.length).toBeLessThanOrEqual(3 * pageSize + 1);
            expect(resultKeys).toEqual([95, 61, 60, 50, 44, 41, 17]);
        });

        test("query key exists, query key at top", () => {
            const queryKey = 100;
            const summarize = buildContentResult({ keyDirection, pageSize, getKey });

            // choose a hid we know is in the results
            const { contents, targetKey, startKey, startKeyIndex } = summarize([updateList, queryKey]);

            expect(startKey).toEqual(queryKey);
            expect(startKeyIndex).toEqual(0);
            expect(targetKey).toEqual(queryKey);

            const resultKeys = contents.map(getKey);
            // match (top) + 2 pages after
            expect(resultKeys).toEqual([100, 95, 61, 60, 50]);
        });

        test("query key exists, query key at bottom", () => {
            const queryKey = 1;
            const summarize = buildContentResult({ keyDirection, pageSize, getKey });

            // choose a hid we know is in the results
            const { contents, targetKey, startKey, startKeyIndex } = summarize([updateList, queryKey]);

            expect(startKey).toEqual(queryKey);
            expect(startKeyIndex).toEqual(2);
            expect(targetKey).toEqual(queryKey);

            const resultKeys = contents.map(getKey);
            expect(resultKeys).toEqual([41, 17, 1]);
        });

        test("query key doesn't exist, query key in middle", () => {
            const queryKey = 51;
            const summarize = buildContentResult({ keyDirection, pageSize, getKey });

            // choose a hid we know is in the results
            const { contents, targetKey, startKey, startKeyIndex } = summarize([updateList, queryKey]);

            expect(startKey).toEqual(50);
            expect(startKeyIndex).toEqual(2);
            expect(targetKey).toEqual(queryKey);

            const resultKeys = contents.map(getKey);
            expect(resultKeys).toEqual([61, 60, 50, 44, 41, 17]);
        });

        test("query key doesn't exist, query key near top", () => {
            const queryKey = 99;
            const summarize = buildContentResult({ keyDirection, pageSize, getKey });

            // choose a hid we know is in the results
            const { contents, targetKey, startKey, startKeyIndex } = summarize([updateList, queryKey]);

            expect(startKey).toEqual(100);
            expect(startKeyIndex).toEqual(0);
            expect(targetKey).toEqual(queryKey);

            const resultKeys = contents.map(getKey);
            expect(resultKeys).toEqual([100, 95, 61, 60, 50]);
        });

        test("query key doesn't exist, query key near bottom", () => {
            const queryKey = 16;
            const summarize = buildContentResult({ keyDirection, pageSize, getKey });

            // choose a hid we know is in the results
            const { contents, targetKey, startKey, startKeyIndex } = summarize([updateList, queryKey]);

            expect(startKey).toEqual(17);
            expect(startKeyIndex).toEqual(1);
            expect(targetKey).toEqual(queryKey);

            const resultKeys = contents.map(getKey);
            expect(resultKeys).toEqual([41, 17, 1]);
        });

        test("query key beyond upper limit", () => {
            const queryKey = 200;
            const summarize = buildContentResult({ keyDirection, pageSize, getKey });

            // choose a hid we know is in the results
            const { contents, targetKey, startKey, startKeyIndex } = summarize([updateList, queryKey]);

            expect(startKey).toEqual(100);
            expect(startKeyIndex).toEqual(0);
            expect(targetKey).toEqual(queryKey);

            const resultKeys = contents.map(getKey);
            expect(resultKeys).toEqual([100, 95, 61, 60]);
        });

        test("query key below lower limit", () => {
            const queryKey = -300;
            const summarize = buildContentResult({ keyDirection, pageSize, getKey });

            // choose a hid we know is in the results
            const { contents, targetKey, startKey, startKeyIndex } = summarize([updateList, queryKey]);

            expect(startKey).toEqual(1);
            expect(startKeyIndex).toEqual(1);
            expect(targetKey).toEqual(queryKey);

            const resultKeys = contents.map(getKey);
            expect(resultKeys).toEqual([17, 1]);
        });
    });

    describe("query collection content from aggregate storage", () => {
        const updateList = new SkipList();

        // collection content is keyed by element_index, ascending order
        const keyDirection = SEEK.ASC;
        const getKey = (item) => item.element_index;
        const pageSize = 2;

        // sample content, indexed by hid
        const element_indexes = [1, 2, 3, 4, 5, 6, 7, 8, 9];
        element_indexes.forEach((i) => updateList.upsert(i, { element_index: i }));

        test("query key exists, query key in middle", () => {
            const queryKey = 5;
            const summarize = buildContentResult({ keyDirection, pageSize, getKey });

            // choose a hid we know is in the results
            const { contents, targetKey, startKey, startKeyIndex } = summarize([updateList, queryKey]);

            expect(startKey).toEqual(queryKey);
            expect(startKeyIndex).toEqual(2);
            expect(targetKey).toEqual(queryKey);

            const resultKeys = contents.map(getKey);
            expect(resultKeys).toEqual([3, 4, 5, 6, 7, 8, 9]);
        });

        test("query key exists, query key at top", () => {
            const queryKey = 1;
            const summarize = buildContentResult({ keyDirection, pageSize, getKey });

            // choose a hid we know is in the results
            const { contents, targetKey, startKey, startKeyIndex } = summarize([updateList, queryKey]);

            expect(startKey).toEqual(queryKey);
            expect(startKeyIndex).toEqual(0);
            expect(targetKey).toEqual(queryKey);

            const resultKeys = contents.map(getKey);
            expect(resultKeys).toEqual([1, 2, 3, 4, 5]);
        });

        test("query key exists, query key at bottom", () => {
            const queryKey = 9;
            const summarize = buildContentResult({ keyDirection, pageSize, getKey });

            // choose a hid we know is in the results
            const { contents, targetKey, startKey, startKeyIndex } = summarize([updateList, queryKey]);

            expect(startKey).toEqual(queryKey);
            expect(startKeyIndex).toEqual(2);
            expect(targetKey).toEqual(queryKey);

            const resultKeys = contents.map(getKey);
            expect(resultKeys).toEqual([7, 8, 9]);
        });

        test("query key doesn't exist, query key in middle", () => {
            const queryKey = 4.2;
            const summarize = buildContentResult({ keyDirection, pageSize, getKey });

            // choose a hid we know is in the results
            const { contents, targetKey, startKey, startKeyIndex } = summarize([updateList, queryKey]);

            expect(startKey).toEqual(4);
            expect(startKeyIndex).toEqual(1);
            expect(targetKey).toEqual(queryKey);

            const resultKeys = contents.map(getKey);
            expect(resultKeys).toEqual([3, 4, 5, 6, 7, 8]);
        });

        test("query key doesn't exist, query key near top", () => {
            const queryKey = 0.8;
            const summarize = buildContentResult({ keyDirection, pageSize, getKey });

            // choose a hid we know is in the results
            const { contents, targetKey, startKey, startKeyIndex } = summarize([updateList, queryKey]);

            expect(startKey).toEqual(1);
            expect(startKeyIndex).toEqual(0);
            expect(targetKey).toEqual(queryKey);

            const resultKeys = contents.map(getKey);
            expect(resultKeys).toEqual([1, 2, 3, 4]);
        });

        test("query key doesn't exist, query key near bottom", () => {
            const queryKey = 8.1;
            const summarize = buildContentResult({ keyDirection, pageSize, getKey });

            // choose a hid we know is in the results
            const { contents, targetKey, startKey, startKeyIndex } = summarize([updateList, queryKey]);

            expect(startKey).toEqual(8);
            expect(startKeyIndex).toEqual(1);
            expect(targetKey).toEqual(queryKey);

            const resultKeys = contents.map(getKey);
            expect(resultKeys).toEqual([7, 8, 9]);
        });

        test("query key beyond upper limit", () => {
            const queryKey = -1999;
            const summarize = buildContentResult({ keyDirection, pageSize, getKey });

            // choose a hid we know is in the results
            const { contents, targetKey, startKey, startKeyIndex } = summarize([updateList, queryKey]);

            expect(startKey).toEqual(1);
            expect(startKeyIndex).toEqual(0);
            expect(targetKey).toEqual(queryKey);

            const resultKeys = contents.map(getKey);
            expect(resultKeys).toEqual([1, 2, 3, 4]);
        });

        test("query key below lower limit", () => {
            const queryKey = 300;
            const summarize = buildContentResult({ keyDirection, pageSize, getKey });

            // choose a hid we know is in the results
            const { contents, targetKey, startKey, startKeyIndex } = summarize([updateList, queryKey]);

            expect(startKey).toEqual(9);
            expect(startKeyIndex).toEqual(1);
            expect(targetKey).toEqual(queryKey);

            const resultKeys = contents.map(getKey);
            expect(resultKeys).toEqual([8, 9]);
        });
    });
});

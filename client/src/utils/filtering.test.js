import { describe, expect, test } from "vitest";

import { HistoryFilters } from "@/components/History/HistoryFilters";
import { getHistoryListFilters } from "@/components/History/historyList";
import Filtering, { contains, equals } from "@/utils/filtering";

const filterSyntaxCases = [
    {
        syntax: "comparison operators and single quotes",
        text: "name:'name of item' hid>10 hid<100 create-time>'2021-01-01' update-time<'2022-01-01' state:success extension:ext tag:first deleted:False visible:'TRUE'",
        visible: "TRUE",
    },
    {
        syntax: "comparison aliases and mixed quotes",
        text: 'name:"name of item" hid_gt:10 hid-lt:100 create_time-gt:"2021-01-01" update_time-lt:\'2022-01-01\' state:sUccEss extension:EXT tag:FirsT deleted:false visible:true',
        visible: "true",
    },
];
const sampleFilters = [
    {
        scenario: "boolean conversion with null and unknown filters",
        filters: { deleted: "true", visible: null, invalid: "value" },
        validFilters: { deleted: true },
        invalidFilters: { invalid: "value", visible: null },
        validText: "deleted:true visible:any",
    },
    {
        scenario: "any and numeric filters with an unsupported comparison alias",
        filters: { deleted: "any", related: 10, hid_gt: 5, hid_less_than: 20 },
        validFilters: { deleted: "any", related: 10, hid_gt: 5 },
        invalidFilters: { hid_less_than: 20 },
        validText: "deleted:any related:10 hid>5 visible:any",
    },
];

const expectedParsedFilters = {
    name: "name of item",
    hid_gt: "10",
    hid_lt: "100",
    create_time_gt: "2021-01-01",
    update_time_lt: "2022-01-01",
    state: "success",
    extension: "ext",
    tag: "first",
    deleted: "false",
    visible: "true",
};

const matchingHistoryItem = {
    create_time: "2021-06-01",
    extension: "ext",
    deleted: false,
    hid: 11,
    name: "contains the name of item.",
    state: "success",
    tags: ["first", "second"],
    update_time: "2021-06-01",
    visible: true,
};

const localMatchCases = [
    { scenario: "all filters match", overrides: {}, matches: true },
    { scenario: "index at lower bound", overrides: { hid: 10 }, matches: false },
    { scenario: "index at upper bound", overrides: { hid: 100 }, matches: false },
    { scenario: "index below upper bound", overrides: { hid: 99 }, matches: true },
    { scenario: "different state", overrides: { state: "error" }, matches: false },
    { scenario: "creation date at lower bound", overrides: { create_time: "2021-01-01" }, matches: false },
    { scenario: "creation date above lower bound", overrides: { create_time: "2021-01-02" }, matches: true },
    { scenario: "update date at upper bound", overrides: { update_time: "2022-01-01" }, matches: false },
    { scenario: "update date below upper bound", overrides: { update_time: "2021-12-31" }, matches: true },
    { scenario: "missing required tag", overrides: { tags: ["second"] }, matches: false },
    { scenario: "hidden item", overrides: { visible: false }, matches: false },
    { scenario: "deleted item", overrides: { deleted: true }, matches: false },
    { scenario: "non-true deleted value", overrides: { deleted: "nottrue" }, matches: true },
];

describe("history content filters", () => {
    test.each([
        ["empty search", "", { deleted: false, visible: true }],
        ["explicit deleted flag", "deleted:true", { deleted: true }],
        ["explicit visibility flag", "visible:false", { visible: false }],
        ["non-default filter", "extension:ext", { "extension-eq": "ext", deleted: false, visible: true }],
    ])("applies default filters for %s", (_scenario, text, expectedQuery) => {
        // Exact equality also checks that explicitly setting one default does not insert the other.
        expect(HistoryFilters.getQueryDict(text)).toEqual(expectedQuery);
    });

    test("uses unspecified text as the name filter", () => {
        const filters = HistoryFilters.getFiltersForText("name of item");
        expect(filters[0]).toEqual(["name", "name of item"]);
        expect(HistoryFilters.getQueryDict("name of item")["name-contains"]).toBe("name of item");
    });

    test("removes any from default filters but keeps it as a literal name", () => {
        expect(HistoryFilters.getFiltersForText("deleted:any")).toEqual([]);
        expect(HistoryFilters.getQueryDict("deleted:any")).toEqual({});
        expect(HistoryFilters.getFiltersForText("name:any")[0]).toEqual(["name", "any"]);
    });

    test.each([
        ["name", "name of item", true],
        ["tag", "first", true],
        ["tag", "second", false],
        ["deleted", "false", true],
        ["visible", true, true],
        ["visible", "false", false],
    ])("checks %s against %s: %s", (key, value, matches) => {
        expect(HistoryFilters.checkFilter(filterSyntaxCases[0].text, key, value)).toBe(matches);
    });

    test.each([
        ["name", "name of item"],
        ["hid_gt", "10"],
        ["hid_lt", "100"],
        ["tag", "first"],
        ["deleted", false],
        ["visible", true],
        ["invalid", undefined],
    ])("reads %s from operator syntax", (key, expectedValue) => {
        expect(HistoryFilters.getFilterValue(filterSyntaxCases[0].text, key)).toBe(expectedValue);
    });

    test.each([
        ["hid_gt", false, "10"],
        ["create_time_gt", false, "2021-01-01"],
        ["create_time_gt", true, 1609459200],
    ])("reads %s from alias syntax with backend formatting %s", (key, backendFormatted, expectedValue) => {
        expect(HistoryFilters.getFilterValue(filterSyntaxCases[1].text, key, backendFormatted)).toBe(expectedValue);
    });

    test.each([
        ["deleted", false],
        ["visible", true],
    ])("reads the default %s from an empty search", (key, expectedValue) => {
        expect(HistoryFilters.getFilterValue("", key)).toBe(expectedValue);
    });

    test.each([
        ["name", undefined],
        ["name_eq", "select"],
    ])("reads %s from an explicit exact-name filter", (key, expectedValue) => {
        expect(HistoryFilters.getFilterValue("name_eq:Select", key)).toBe(expectedValue);
    });

    test.each(sampleFilters)(
        "validates and serializes $scenario",
        ({ filters, validFilters, invalidFilters, validText }) => {
            expect(HistoryFilters.getValidFilters(filters)).toEqual({ validFilters, invalidFilters });
            expect(HistoryFilters.getFilterText(filters)).toBe(validText);
        },
    );

    describe.each(filterSyntaxCases)("$syntax", ({ text, visible }) => {
        test("parses normalized filter entries in their original order", () => {
            expect(HistoryFilters.getFiltersForText(text)).toEqual(
                Object.entries({ ...expectedParsedFilters, visible }),
            );
        });

        test("converts filter entries to a query dictionary", () => {
            const query = HistoryFilters.getQueryDict(text);
            expect(query).toEqual({
                "name-contains": "name of item",
                "hid-gt": "10",
                "hid-lt": "100",
                "create_time-gt": 1609459200,
                "update_time-lt": 1640995200,
                "state-eq": "success",
                "extension-eq": "ext",
                tag: "first",
                deleted: false,
                visible: true,
            });
            expect(query["name-eq"]).toBeUndefined();
        });

        test("synchronizes parsed filter keys and values", () => {
            expect(Object.fromEntries(HistoryFilters.getFiltersForText(text))).toEqual({
                ...expectedParsedFilters,
                visible,
            });
        });

        test.each(localMatchCases)("matches a history item: $scenario", ({ overrides, matches }) => {
            const filters = HistoryFilters.getFiltersForText(text);
            expect(HistoryFilters.testFilters(filters, { ...matchingHistoryItem, ...overrides })).toBe(matches);
        });
    });

    test("parses an explicit exact genome-build filter", () => {
        expect(HistoryFilters.getFiltersForText('genome_build_eq:"hg19"')[0]).toEqual(["genome_build_eq", "hg19"]);
    });

    test("routes an explicit exact-name filter to name-eq", () => {
        expect(HistoryFilters.getQueryDict("name_eq:'name of item'")["name-eq"]).toBe("name of item");
    });

    test.each([
        {
            scenario: "ignores invalid filters while converting a deleted flag",
            filters: sampleFilters[0].filters,
            text: "",
            remove: false,
            expected: "deleted:true visible:true",
        },
        {
            scenario: "adds numeric filters alongside any and default visibility",
            filters: sampleFilters[1].filters,
            text: "",
            remove: false,
            expected: "deleted:any visible:true related:10 hid>5",
        },
        {
            scenario: "adds comparison, state, and tag filters",
            filters: { hid_lt: 100, create_time_gt: "2021-01-01", state: "success", tag: "first" },
            text: "",
            remove: false,
            expected: "hid<100 create_time>2021-01-01 state:success tag:first",
        },
        {
            scenario: "removes only the specified filters from an existing search",
            filters: { hid_lt: 100, create_time_gt: "2021-01-01", state: "success", tag: "first" },
            text: filterSyntaxCases[0].text,
            remove: true,
            expected: "name:'name of item' hid>10 update_time<2022-01-01 extension:ext",
        },
        {
            scenario: "keeps explicit any and visibility filters",
            filters: { deleted: "any", visible: true },
            text: "",
            remove: false,
            expected: "deleted:any visible:true",
        },
        {
            scenario: "restores any when removing a default filter from an existing search",
            filters: { deleted: "any" },
            text: "deleted:any visible:true",
            remove: true,
            expected: "visible:true deleted:any",
        },
    ])("applies filters: $scenario", ({ filters, text, remove, expected }) => {
        expect(HistoryFilters.applyFiltersToText(filters, text, remove)).toBe(expected);
    });

    test.each([
        ["", "deleted", "any", "deleted:any visible:true"],
        ["deleted:any visible:true", "deleted", "false", ""],
        ["", "deleted", "true", "deleted:true visible:true"],
        ["hid<299", "create_time_gt", "11-09-1981", "hid<299 create_time>11-09-1981"],
        ["hid<299", "create_time_lt", "11-09-1981", "hid<299 create_time<11-09-1981"],
        ["hid<299", "a_created_time_gt", "11-09-1981", "hid<299"],
    ])("sets %s: %s=%s -> %s", (text, key, value, expectedText) => {
        expect(HistoryFilters.setFilterValue(text, key, value)).toBe(expectedText);
    });

    test.each([
        ["tag:#test", "#test"],
        ["tag:'#test me'", "#test me"],
        ['tag:"#test me"', "#test me"],
    ])("parses a named tag from %s", (text, value) => {
        expect(HistoryFilters.getFiltersForText(text)[0]).toEqual(["tag", value]);
    });

    test("converts a hash-prefixed tag to a backend name tag", () => {
        expect(HistoryFilters.getQueryDict("tag:#test")["tag"]).toBe("name:test");
    });
});

/**
 * Quoting a keyed value (`name:'GREP'`) groups whitespace and preserves case, but is not itself
 * an exact-match request -- the backend query still uses the filter's normal `-contains`/`-eq`
 * handler. An unquoted value (`name:grep`) is folded to lower case. Exact match for a keyed
 * filter is requested with its dedicated `_eq` key (`name_eq:GREP`).
 */
describe("quoted filter values (case preserved, grouped, not routed to _eq)", () => {
    // A filter set with a `name`/`name_eq` sibling pair and no default filters, so the
    // parsed output isn't padded with `deleted`/`visible` defaults.
    const filters = new Filtering(
        {
            name: { type: String, handler: contains("name"), menuItem: true },
            name_eq: { handler: equals("name"), menuItem: false },
            state: { type: String, handler: equals("state"), menuItem: true },
        },
        undefined,
        true,
    );

    test("getFiltersForText keeps original case for quoted values, folds unquoted", () => {
        expect(Object.fromEntries(filters.getFiltersForText("name:'GREP'"))).toEqual({ name: "GREP" });
        expect(Object.fromEntries(filters.getFiltersForText("name:GREP"))).toEqual({ name: "grep" });
        expect(Object.fromEntries(filters.getFiltersForText('name:"GREP"'))).toEqual({ name: "GREP" });
    });

    test("getFiltersForText strips the surrounding quotes from the stored value", () => {
        const [[, value]] = filters.getFiltersForText("name:'GREP'");
        expect(value).toBe("GREP");
        expect(value).not.toContain("'");
    });

    test("getQueryDict keeps a quoted keyed value on the normal -contains handler", () => {
        // quoted -> case preserved, but still `-contains`
        expect(filters.getQueryDict("name:'GREP'")).toEqual({ "name-contains": "GREP" });
        // unquoted -> case-insensitive substring, lowercased
        expect(filters.getQueryDict("name:GREP")).toEqual({ "name-contains": "grep" });
    });

    test("getQueryDict routes the explicit name_eq: key to an exact match", () => {
        expect(filters.getQueryDict("name_eq:GREP")).toEqual({ "name-eq": "grep" });
        expect(filters.getQueryDict("name_eq:'GREP'")).toEqual({ "name-eq": "GREP" });
    });

    test("getQueryString emits the case-preserved, still-contains query", () => {
        expect(filters.getQueryString("name:'GREP'")).toBe("q=name-contains&qv=GREP");
        expect(filters.getQueryString("name:grep")).toBe("q=name-contains&qv=grep");
    });

    test("a quoted value with no _eq sibling still strips quotes and preserves case", () => {
        expect(filters.getQueryDict("state:'OK'")).toEqual({ "state-eq": "OK" });
    });

    test("getFilterText re-serializes a quoted single-word value unquoted", () => {
        // the quotes carried no distinct meaning once parsed, so they don't come back
        expect(filters.getFilterText({ name: "GREP" }, false, "name:'GREP'")).toBe("name:GREP");
        expect(filters.getFilterText({ name: "grep" }, false, "name:grep")).toBe("name:grep");
    });

    test("getFilterText keeps quoting values that contain a space", () => {
        expect(filters.getFilterText({ name: "name of item" })).toBe("name:'name of item'");
    });

    test("getFilterValue returns the case-preserved value for a quoted filter", () => {
        expect(filters.getFilterValue("name:'GREP'", "name")).toBe("GREP");
        expect(filters.getFilterValue("name:grep", "name")).toBe("grep");
    });

    test("local testFilters matching is unaffected by quoting (stays case-insensitive)", () => {
        const quoted = HistoryFilters.getFiltersForText("name:'GREP'");
        const unquoted = HistoryFilters.getFiltersForText("name:grep");
        const item = { name: "my grep tool", deleted: false, visible: true };
        expect(HistoryFilters.testFilters(quoted, { ...item })).toBe(true);
        expect(HistoryFilters.testFilters(unquoted, { ...item })).toBe(true);
    });

    test("checkFilter stays case-insensitive for quoted values", () => {
        expect(HistoryFilters.checkFilter("name:'GREP'", "name", "grep")).toBe(true);
    });
});

/**
 * A single quoted bare token (`'Grep1'` typed on its own, with no `key:`) is an exact-match
 * request for the `autoFilterKey`: the quotes are stripped from the folded value, and the query
 * routes through the `_eq` handler. An unquoted bare token, or
 * more than one bare token, stays a plain case-insensitive substring search.
 */
describe("a lone quoted bare token routes autoFilterKey through exact match", () => {
    const filters = new Filtering(
        {
            search: { type: String, handler: contains("search"), menuItem: true },
            search_eq: { handler: equals("search"), menuItem: false },
        },
        undefined,
        true,
        "search",
    );

    test("getFiltersForText strips the quotes when folding into autoFilterKey", () => {
        expect(Object.fromEntries(filters.getFiltersForText("'Grep1'"))).toEqual({ search: "Grep1" });
        // an unquoted bare token is folded verbatim (the backend lowercases a `-contains` search)
        expect(Object.fromEntries(filters.getFiltersForText("Grep1"))).toEqual({ search: "Grep1" });
    });

    test("getQueryDict routes the lone quoted bare token to the _eq handler", () => {
        expect(filters.getQueryDict("'Grep1'")).toEqual({ "search-eq": "Grep1" });
        expect(filters.getQueryDict("Grep1")).toEqual({ "search-contains": "Grep1" });
    });

    test("more than one bare token is a plain search, not an exact match", () => {
        expect(filters.getQueryDict("foo 'Grep1'")["search-eq"]).toBeUndefined();
    });

    test("getFilterText writes the folded value back unlabeled, keeping its exact-match quotes", () => {
        expect(filters.getFilterText({ search: "Grep1" }, false, "'Grep1'")).toBe("'Grep1'");
        // an unquoted bare token stays unquoted
        expect(filters.getFilterText({ search: "Grep1" }, false, "Grep1")).toBe("Grep1");
    });

    test("the exact-match quotes survive applying another filter alongside the bare token", () => {
        // regression: the `key === unspecifiedTextKey` branch used to write the value before the
        // quoting could be applied, so adding a sibling filter silently dropped the exact match
        // (JobsFilters uses this shape: quoted bare text for an exact tool search, plus state:)
        const filtersWithState = new Filtering(
            {
                search: { type: String, handler: contains("search"), menuItem: true },
                search_eq: { handler: equals("search"), menuItem: false },
                state: { type: String, handler: equals("state"), menuItem: true },
            },
            undefined,
            true,
            "search",
        );
        expect(filtersWithState.applyFiltersToText({ state: "ok" }, "'Grep1'")).toBe("'Grep1' state:ok");
    });
});

describe("quote matching + unspecified text + autoFilterKey combined (JobsFilters-shaped)", () => {
    const jobFilters = new Filtering(
        {
            tool_id: { type: String, handler: contains("tool_id"), menuItem: true },
            tool_id_eq: { handler: equals("tool_id"), menuItem: false },
            state: { type: String, handler: equals("state"), menuItem: true },
        },
        undefined,
        true,
        "tool_id",
    );

    test("unquoted unspecified text is a plain, case-folded contains search", () => {
        expect(jobFilters.getQueryDict("grep1")).toEqual({ "tool_id-contains": "grep1" });
    });

    test("an explicit key:value stays -contains even when quoted", () => {
        expect(jobFilters.getQueryDict("tool_id:foo")).toEqual({ "tool_id-contains": "foo" });
        expect(jobFilters.getQueryDict("tool_id:'Foo'")).toEqual({ "tool_id-contains": "Foo" });
    });

    test("the explicit tool_id_eq: key requests an exact match", () => {
        expect(jobFilters.getQueryDict("tool_id_eq:Foo")).toEqual({ "tool_id-eq": "foo" });
    });

    test("a quoted bare multi-word token is still an exact match (autoFilterKey's own syntax)", () => {
        expect(jobFilters.getQueryDict("'Advanced Cut'")).toEqual({ "tool_id-eq": "Advanced Cut" });
    });

    test("a quoted bare token is an exact match, case preserved", () => {
        expect(jobFilters.getQueryDict("'Grep1'")).toEqual({ "tool_id-eq": "Grep1" });
    });

    test("adding state: alongside a quoted bare token keeps the exact match (regression)", () => {
        const text = jobFilters.applyFiltersToText({ state: "ok" }, "'Grep1'");
        expect(text).toBe("'Grep1' state:ok");
        expect(jobFilters.getQueryDict(text)).toEqual({ "tool_id-eq": "Grep1", "state-eq": "ok" });
    });

    test("adding state: alongside an unquoted bare token stays a plain search", () => {
        const text = jobFilters.applyFiltersToText({ state: "ok" }, "grep1");
        expect(text).toBe("grep1 state:ok");
        expect(jobFilters.getQueryDict(text)).toEqual({ "tool_id-contains": "grep1", "state-eq": "ok" });
    });

    test("unspecified text alongside an explicit key:value does not itself become an exact match", () => {
        // two bare/keyed tokens for the same autoFilterKey -- only a LONE quoted bare token is exact
        expect(jobFilters.getQueryDict("grep1 tool_id:foo")["tool_id-eq"]).toBeUndefined();
    });
});

/**
 * A keyed value's quotes are purely syntactic (grouping whitespace, preserving case) at any word
 * count, whether the user typed them or `getFilterText` added them to keep a value with a space
 * as one token. Neither case routes to the sibling `_eq` handler.
 */
describe("quoting a keyed value never implies exact match, at any word count", () => {
    test("getFilterText -> getQueryDict round-trip: a multi-word contains value stays contains", () => {
        const text = HistoryFilters.getFilterText({
            name: "foo bar",
            ...HistoryFilters.defaultFilters,
        });
        expect(text).toBe("name:'foo bar'");
        expect(HistoryFilters.getQueryDict(text)).toMatchObject({ "name-contains": "foo bar" });
        expect(HistoryFilters.getQueryDict(text)["name-eq"]).toBeUndefined();
    });

    test("a user-typed single-word quote also stays a contains search", () => {
        expect(HistoryFilters.getQueryDict("name:'GREP'")).toMatchObject({ "name-contains": "GREP" });
        expect(HistoryFilters.getQueryDict("name:'GREP'")["name-eq"]).toBeUndefined();
    });

    test("duplicate keys: the surviving occurrence's value and case win, both stay -contains", () => {
        expect(HistoryFilters.getQueryDict("name:'Exact' name:partial")).toMatchObject({
            "name-contains": "partial",
        });
        expect(HistoryFilters.getQueryDict("name:partial name:'Exact'")).toMatchObject({
            "name-contains": "Exact",
        });
    });
});

describe("plain text next to a MultiTags filter (history list advanced search)", () => {
    const filters = getHistoryListFilters("published");

    test("plain text stays separate from the tag across re-serialization", () => {
        const text = filters.getFilterText(
            Object.fromEntries(filters.getFiltersForText("abc tag:mytag", true, false)),
            false,
            "abc tag:mytag",
        );
        expect(text).toBe("abc tag:mytag");
        expect(Object.fromEntries(filters.getFiltersForText(text, true, false))).toEqual({
            name: "abc",
            tag: ["mytag"],
        });
    });

    test("setting the name after the tag keeps both filters", () => {
        const text = filters.setFilterValue(filters.setFilterValue("", "tag", "mytag"), "name", "abc");
        expect(Object.fromEntries(filters.getFiltersForText(text, true, false))).toEqual({
            name: "abc",
            tag: ["mytag"],
        });
    });
});

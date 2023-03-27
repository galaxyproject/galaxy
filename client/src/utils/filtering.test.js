import { HistoryFilters } from "@/components/History/HistoryFilters";

const filterTexts = [
    "name:'name of item' hid>10 hid<100 create-time>'2021-01-01' update-time<'2022-01-01' state:success extension:ext tag:first deleted:False visible:'TRUE'",
    'name:"name of item" hid_gt:10 hid-lt:100 create_time-gt:"2021-01-01" update_time-lt:\'2022-01-01\' state:sUccEss extension:EXT tag:FirsT deleted:false visible:true',
];

describe("filtering", () => {
    test("parse default filter", () => {
        let queryDict = HistoryFilters.getQueryDict("");
        expect(queryDict["deleted"]).toBe(false);
        expect(queryDict["visible"]).toBe(true);
        queryDict = HistoryFilters.getQueryDict("deleted:true");
        expect(queryDict["deleted"]).toBe(true);
        expect(queryDict["visible"]).toBeUndefined();
        queryDict = HistoryFilters.getQueryDict("visible:false");
        expect(queryDict["deleted"]).toBeUndefined;
        expect(queryDict["visible"]).toBe(false);
        queryDict = HistoryFilters.getQueryDict("extension:ext");
        expect(queryDict["extension-eq"]).toBe("ext");
        expect(queryDict["deleted"]).toBe(false);
        expect(queryDict["visible"]).toBe(true);
    });
    test("parse name filter", () => {
        const filters = HistoryFilters.getFilters("name of item");
        expect(filters[0][0]).toBe("name");
        expect(filters[0][1]).toBe("name of item");
        const queryDict = HistoryFilters.getQueryDict("name of item");
        expect(queryDict["name-contains"]).toBe("name of item");
    });
    test("parse any for default parameters", () => {
        const filters = HistoryFilters.getFilters("deleted:any");
        expect(filters.length).toBe(0);
        const queryDict = HistoryFilters.getQueryDict("deleted:any");
        expect(Object.keys(queryDict).length).toBe(0);
        const filtersAny = HistoryFilters.getFilters("name:any");
        expect(filtersAny[0][0]).toBe("name");
        expect(filtersAny[0][1]).toBe("any");
    });
    test("parse check filter", () => {
        expect(HistoryFilters.checkFilter(filterTexts[0], "name", "name of item")).toBe(true);
        expect(HistoryFilters.checkFilter(filterTexts[0], "tag", "first")).toBe(true);
        expect(HistoryFilters.checkFilter(filterTexts[0], "tag", "second")).toBe(false);
        expect(HistoryFilters.checkFilter(filterTexts[0], "deleted", "false")).toBe(true);
        expect(HistoryFilters.checkFilter(filterTexts[0], "visible", true)).toBe(true);
        expect(HistoryFilters.checkFilter(filterTexts[0], "visible", "false")).toBe(false);
    });
    test("parse get filter value", () => {
        expect(HistoryFilters.getFilterValue(filterTexts[0], "name")).toBe("name of item");
        expect(HistoryFilters.getFilterValue(filterTexts[0], "hid", "gt")).toBe("10");
        expect(HistoryFilters.getFilterValue(filterTexts[0], "hid", "lt")).toBe("100");
        expect(HistoryFilters.getFilterValue(filterTexts[0], "tag")).toBe("first");
        expect(HistoryFilters.getFilterValue(filterTexts[0], "deleted")).toBe("False");
        expect(HistoryFilters.getFilterValue(filterTexts[0], "visible")).toBe("TRUE");
        expect(HistoryFilters.getFilterValue(filterTexts[1], "hid", "gt")).toBe("10");
        expect(HistoryFilters.getFilterValue(filterTexts[1], "create_time", "gt")).toBe("2021-01-01");
    });
    test("parse filter text as entries", () => {
        filterTexts.forEach((filterText) => {
            const filters = HistoryFilters.getFilters(filterText);
            expect(filters[0][0]).toBe("name");
            expect(filters[0][1]).toBe("name of item");
            expect(filters[1][0]).toBe("hid_gt");
            expect(filters[1][1]).toBe("10");
            expect(filters[2][0]).toBe("hid_lt");
            expect(filters[2][1]).toBe("100");
            expect(filters[3][0]).toBe("create_time_gt");
            expect(filters[3][1]).toBe("2021-01-01");
            expect(filters[4][0]).toBe("update_time_lt");
            expect(filters[4][1]).toBe("2022-01-01");
            expect(filters[5][0]).toBe("state");
            expect(filters[5][1]).toBe("success");
            expect(filters[6][0]).toBe("extension");
            expect(filters[6][1]).toBe("ext");
            expect(filters[7][0]).toBe("tag");
            expect(filters[7][1]).toBe("first");
            expect(filters[8][0]).toBe("deleted");
            expect(filters[8][1]).toBe("false");
            expect(filters[9][0]).toBe("visible");
            expect(filters[9][1]).toBe("true");
        });
    });
    test("parse filter text as query dictionary", () => {
        filterTexts.forEach((filterText) => {
            const queryDict = HistoryFilters.getQueryDict(filterText);
            expect(queryDict["name-contains"]).toBe("name of item");
            expect(queryDict["hid-gt"]).toBe("10");
            expect(queryDict["hid-lt"]).toBe("100");
            expect(queryDict["create_time-gt"]).toBe(1609459200);
            expect(queryDict["update_time-lt"]).toBe(1640995200);
            expect(queryDict["state-eq"]).toBe("success");
            expect(queryDict["extension-eq"]).toBe("ext");
            expect(queryDict["tag"]).toBe("first");
            expect(queryDict["deleted"]).toBe(false);
            expect(queryDict["visible"]).toBe(true);
        });
    });
    test("validate filtering of a history item", () => {
        const item = {
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
        filterTexts.forEach((filterText) => {
            const filters = HistoryFilters.getFilters(filterText);
            expect(HistoryFilters.testFilters(filters, { ...item })).toBe(true);
            expect(HistoryFilters.testFilters(filters, { ...item, hid: 10 })).toBe(false);
            expect(HistoryFilters.testFilters(filters, { ...item, hid: 100 })).toBe(false);
            expect(HistoryFilters.testFilters(filters, { ...item, hid: 99 })).toBe(true);
            expect(HistoryFilters.testFilters(filters, { ...item, state: "error" })).toBe(false);
            expect(HistoryFilters.testFilters(filters, { ...item, create_time: "2021-01-01" })).toBe(false);
            expect(HistoryFilters.testFilters(filters, { ...item, create_time: "2021-01-02" })).toBe(true);
            expect(HistoryFilters.testFilters(filters, { ...item, update_time: "2022-01-01" })).toBe(false);
            expect(HistoryFilters.testFilters(filters, { ...item, update_time: "2021-12-31" })).toBe(true);
            expect(HistoryFilters.testFilters(filters, { ...item, tags: ["second"] })).toBe(false);
            expect(HistoryFilters.testFilters(filters, { ...item, visible: false })).toBe(false);
            expect(HistoryFilters.testFilters(filters, { ...item, deleted: true })).toBe(false);
            expect(HistoryFilters.testFilters(filters, { ...item, deleted: "nottrue" })).toBe(true);
        });
    });
    test("Parsing & sync of filter settings", () => {
        // Expected parsed settings
        const parsedFilterSettings = {
            "name:": "name of item",
            "hid>": "10",
            "hid<": "100",
            "create_time>": "2021-01-01",
            "update_time<": "2022-01-01",
            "state:": "success",
            "extension:": "ext",
            "tag:": "first",
            "deleted:": "false",
            "visible:": "true",
        };
        // iterate through filterTexts and compare with parsedFilterSettings
        filterTexts.forEach((filterText) => {
            expect(HistoryFilters.toAlias(HistoryFilters.getFilters(filterText))).toEqual(parsedFilterSettings);
        });
    });
    test("named tag (hash) conversion", () => {
        const filters = HistoryFilters.getFilters("tag:#test");
        expect(filters[0][0]).toBe("tag");
        expect(filters[0][1]).toBe("#test");
        const filtersQuote = HistoryFilters.getFilters("tag:'#test me'");
        expect(filtersQuote[0][0]).toBe("tag");
        expect(filtersQuote[0][1]).toBe("#test me");
        const filtersQuoteDouble = HistoryFilters.getFilters('tag:"#test me"');
        expect(filtersQuoteDouble[0][0]).toBe("tag");
        expect(filtersQuoteDouble[0][1]).toBe("#test me");
        const queryDict = HistoryFilters.getQueryDict("tag:#test");
        expect(queryDict["tag"]).toBe("name:test");
    });
});

import { HistoryFilters } from "@/components/History/HistoryFilters";

const filterTexts = [
    "name:'name of item' hid>10 hid<100 create-time>'2021-01-01' update-time<'2022-01-01' state:success extension:ext tag:first deleted:False visible:'TRUE'",
    'name:"name of item" hid_gt:10 hid-lt:100 create_time-gt:"2021-01-01" update_time-lt:\'2022-01-01\' state:sUccEss extension:EXT tag:FirsT deleted:false visible:true',
];
const sampleFilters = [
    {
        filters: {
            deleted: "true",
            visible: null,
            invalid: "value",
        },
        validFilters: {
            deleted: true,
        },
        invalidFilters: {
            invalid: "value",
            visible: null,
        },
        validText: "deleted:true visible:any",
    },
    {
        filters: {
            deleted: "any",
            related: 10,
            hid_gt: 5,
            hid_less_than: 20,
        },
        validFilters: {
            deleted: "any",
            related: 10,
            hid_gt: 5,
        },
        invalidFilters: {
            hid_less_than: 20,
        },
        validText: "deleted:any related:10 hid>5 visible:any",
    },
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
        const filters = HistoryFilters.getFiltersForText("name of item");
        expect(filters[0][0]).toBe("name");
        expect(filters[0][1]).toBe("name of item");
        const queryDict = HistoryFilters.getQueryDict("name of item");
        expect(queryDict["name-contains"]).toBe("name of item");
    });
    test("parse any for default parameters", () => {
        const filters = HistoryFilters.getFiltersForText("deleted:any");
        expect(filters.length).toBe(0);
        const queryDict = HistoryFilters.getQueryDict("deleted:any");
        expect(Object.keys(queryDict).length).toBe(0);
        const filtersAny = HistoryFilters.getFiltersForText("name:any");
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
        expect(HistoryFilters.getFilterValue(filterTexts[0], "hid_gt")).toBe("10");
        expect(HistoryFilters.getFilterValue(filterTexts[0], "hid_lt")).toBe("100");
        expect(HistoryFilters.getFilterValue(filterTexts[0], "tag")).toBe("first");
        expect(HistoryFilters.getFilterValue(filterTexts[0], "deleted")).toBe(false);
        expect(HistoryFilters.getFilterValue(filterTexts[0], "visible")).toBe(true);
        expect(HistoryFilters.getFilterValue(filterTexts[0], "invalid")).toBe(undefined);
        expect(HistoryFilters.getFilterValue(filterTexts[1], "hid_gt")).toBe("10");
        expect(HistoryFilters.getFilterValue(filterTexts[1], "create_time_gt")).toBe("2021-01-01");
        expect(HistoryFilters.getFilterValue(filterTexts[1], "create_time_gt", true)).toBe(1609459200);
        expect(HistoryFilters.getFilterValue("", "deleted")).toBe(false);
        expect(HistoryFilters.getFilterValue("", "visible")).toBe(true);
        expect(HistoryFilters.getFilterValue("name_eq:Select", "name")).toBe(undefined);
        expect(HistoryFilters.getFilterValue("name_eq:Select", "name_eq")).toBe("select");
    });
    test("parse get valid filters and settings", () => {
        sampleFilters.forEach((sample) => {
            const { validFilters, invalidFilters } = HistoryFilters.getValidFilters(sample.filters);
            expect(validFilters).toEqual(sample.validFilters);
            expect(invalidFilters).toEqual(sample.invalidFilters);
            expect(HistoryFilters.getFilterText(sample.filters)).toEqual(sample.validText);
        });
    });
    test("parse filter text as entries", () => {
        filterTexts.forEach((filterText) => {
            const filters = HistoryFilters.getFiltersForText(filterText);
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
            const filters_eq = HistoryFilters.getFiltersForText('genome_build_eq:"hg19"');
            expect(filters_eq[0][0]).toBe("genome_build_eq");
            expect(filters_eq[0][1]).toBe("hg19");
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
        const queryDict = HistoryFilters.getQueryDict("name_eq:'name of item'");
        expect(queryDict["name-eq"]).toBe("name of item");
    });
    test("apply valid filters to existing filterText", () => {
        expect(HistoryFilters.applyFiltersToText(sampleFilters[0].filters, "")).toEqual("deleted:true visible:true");
        expect(HistoryFilters.applyFiltersToText(sampleFilters[1].filters, "")).toEqual(
            "deleted:any visible:true related:10 hid>5"
        );
        expect(
            HistoryFilters.applyFiltersToText(
                { hid_lt: 100, create_time_gt: "2021-01-01", state: "success", tag: "first" },
                ""
            )
        ).toEqual("hid<100 create_time>2021-01-01 state:success tag:first");
        expect(
            HistoryFilters.applyFiltersToText(
                { hid_lt: 100, create_time_gt: "2021-01-01", state: "success", tag: "first" },
                filterTexts[0],
                true
            )
        ).toEqual("name:'name of item' hid>10 update_time<2022-01-01 extension:ext");
        expect(HistoryFilters.applyFiltersToText({ deleted: "any", visible: true }, "")).toEqual(
            "deleted:any visible:true"
        );
        expect(HistoryFilters.applyFiltersToText({ deleted: "any" }, "deleted:any visible:true", true)).toEqual(
            "visible:true deleted:any"
        );
    });
    test("set a single valid filter to existing filterText", () => {
        expect(HistoryFilters.setFilterValue("", "deleted", "any")).toEqual("deleted:any visible:true");
        expect(HistoryFilters.setFilterValue("deleted:any visible:true", "deleted", "false")).toEqual("");
        expect(HistoryFilters.setFilterValue("", "deleted", "true")).toEqual("deleted:true visible:true");
        expect(HistoryFilters.setFilterValue("hid<299", "create_time_gt", "11-09-1981")).toEqual(
            "hid<299 create_time>11-09-1981"
        );
        expect(HistoryFilters.setFilterValue("hid<299", "create_time_lt", "11-09-1981")).toEqual(
            "hid<299 create_time<11-09-1981"
        );
        expect(HistoryFilters.setFilterValue("hid<299", "a_created_time_gt", "11-09-1981")).toEqual("hid<299");
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
            const filters = HistoryFilters.getFiltersForText(filterText);
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
    test("Parsing & sync of filters", () => {
        // Expected parsed filters
        const parsedFilters = {
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
        // iterate through filterTexts and compare with parsedFilters
        filterTexts.forEach((filterText) => {
            expect(Object.fromEntries(HistoryFilters.getFiltersForText(filterText))).toEqual(parsedFilters);
        });
    });
    test("named tag (hash) conversion", () => {
        const filters = HistoryFilters.getFiltersForText("tag:#test");
        expect(filters[0][0]).toBe("tag");
        expect(filters[0][1]).toBe("#test");
        const filtersQuote = HistoryFilters.getFiltersForText("tag:'#test me'");
        expect(filtersQuote[0][0]).toBe("tag");
        expect(filtersQuote[0][1]).toBe("#test me");
        const filtersQuoteDouble = HistoryFilters.getFiltersForText('tag:"#test me"');
        expect(filtersQuoteDouble[0][0]).toBe("tag");
        expect(filtersQuoteDouble[0][1]).toBe("#test me");
        const queryDict = HistoryFilters.getQueryDict("tag:#test");
        expect(queryDict["tag"]).toBe("name:test");
    });
});

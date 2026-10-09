import { describe, expect, it } from "vitest";

import { HistoryFilters } from "@/components/History/HistoryFilters";
import { getHistoryListFilters } from "@/components/History/historyList";
import { quoteToolTagValue } from "@/components/Panels/utilities";
import { getWorkflowFilters } from "@/components/Workflow/List/workflowFilters";
import Filtering, { contains } from "@/utils/filtering";

function makeMixedFilters() {
    return {
        deleted: false,
        visible: true,
        name: "name",
        other: "other",
        tag: ["tag1", "'tag2'", "'#tag3'"],
        genome_build: "",
        published: true,
    };
}

function parseValidFilters(filtering, text) {
    return filtering.getValidFilters(Object.fromEntries(filtering.getFiltersForText(text))).validFilters;
}

// Exercise list components' normalization pattern with real Filtering instances.
// This helper does not exercise the components' own wiring.
function validatedFilterText(filtering, text) {
    const rawFilters = Object.fromEntries(filtering.getFiltersForText(text, true, false));
    if (Object.keys(rawFilters).length === 0) {
        return text;
    }
    const validFilters = filtering.getValidFilters(rawFilters, true).validFilters;
    return filtering.getFilterText(validFilters, true, text);
}

describe("filter objects to text", () => {
    it("defaults history filters to undeleted, visible items", () => {
        expect(HistoryFilters.defaultFilters).toEqual({ deleted: false, visible: true });
    });

    it.each([
        { name: "default values", filters: { deleted: false, visible: true }, expected: true },
        { name: "deleted items", filters: { deleted: true, visible: true }, expected: false },
        { name: "hidden items", filters: { deleted: false, visible: false }, expected: false },
        { name: "uppercase visibility", filters: { deleted: false, visible: "TRUE" }, expected: true },
    ])("recognizes history defaults for $name", ({ filters, expected }) => {
        expect(HistoryFilters.containsDefaults(filters)).toBe(expected);
    });

    it.each([
        { name: "logged-in users", anonymous: false, expected: ["shared_with_me"] },
        { name: "anonymous users", anonymous: true, expected: [] },
    ])("validates shared_with_me in published workflows for $name", ({ anonymous, expected }) => {
        const filtering = getWorkflowFilters("published", anonymous);
        expect(Object.keys(filtering.getValidFilters({ shared_with_me: true }).validFilters)).toEqual(expected);
    });

    it.each([
        { name: "histories", filtering: HistoryFilters, expected: ["deleted", "visible", "name"] },
        {
            name: "my workflows",
            filtering: getWorkflowFilters("my"),
            expected: ["deleted", "name", "tag", "published"],
        },
        { name: "published workflows", filtering: getWorkflowFilters("published"), expected: ["name", "tag"] },
    ])("retains only supported filter keys for $name", ({ filtering, expected }) => {
        expect(Object.keys(filtering.getValidFilters(makeMixedFilters()).validFilters)).toEqual(expected);
    });

    it("omits default history values again after visibility is restored", () => {
        const filters = makeMixedFilters();
        expect(HistoryFilters.getFilterText(filters)).toBe("name:name");

        filters.visible = false;
        expect(HistoryFilters.getFilterText(filters)).toBe("deleted:false visible:false name:name");

        filters.visible = true;
        expect(HistoryFilters.getFilterText(filters)).toBe("name:name");
    });

    it.each([
        {
            name: "my workflows in display text",
            list: "my",
            backend: false,
            published: true,
            expected: "name:name tag:tag1 tag:'tag2' tag:'#tag3' is:published",
        },
        {
            name: "my workflows in backend text",
            list: "my",
            backend: true,
            published: true,
            expected: "name:name tag:tag1 tag:'tag2' tag:'name:tag3' is:published",
        },
        {
            name: "published workflows in backend text",
            list: "published",
            backend: true,
            published: true,
            expected: "name:name tag:tag1 tag:'tag2' tag:'name:tag3'",
        },
        {
            name: "my workflows without the published filter",
            list: "my",
            backend: true,
            published: false,
            expected: "name:name tag:tag1 tag:'tag2' tag:'name:tag3'",
        },
    ])("converts tags and publication filters for $name", ({ list, backend, published, expected }) => {
        const filters = makeMixedFilters();
        if (!published) {
            delete filters.published;
        }
        expect(getWorkflowFilters(list).getFilterText(filters, backend)).toBe(expected);
    });

    it("uses the tool tag converter to quote multi-word MultiTags values", () => {
        const filtering = new Filtering(
            {
                tag: { type: "MultiTags", handler: contains("tag", undefined, quoteToolTagValue), menuItem: true },
            },
            undefined,
            false,
        );

        expect(filtering.getFilterText({ tag: ["data cleanup", "collection_ops"] })).toBe(
            'tag:"data cleanup" tag:collection_ops',
        );
    });
});

describe("filter text to objects", () => {
    it.each([
        { text: "", expected: true },
        { text: "deleted:true", expected: false },
        { text: "visible:false", expected: false },
        { text: "deleted:any", expected: false },
        { text: "deleted:false visible:true", expected: true },
    ])("recognizes history defaults in '$text'", ({ text, expected }) => {
        expect(HistoryFilters.containsDefaults(parseValidFilters(HistoryFilters, text))).toBe(expected);
    });

    it.each([
        { text: "name:name", expected: { deleted: false, visible: true, name: "name" } },
        { text: "visible:false name:name", expected: { visible: false, name: "name" } },
        { text: "visible:false deleted:any name:name", expected: { visible: false, name: "name" } },
        { text: "visible:false deleted:true name:name", expected: { deleted: true, visible: false, name: "name" } },
        {
            text: "visible:false deleted:true name:name invalid:invalid",
            expected: { deleted: true, visible: false, name: "name" },
        },
    ])("parses history filters from '$text'", ({ text, expected }) => {
        expect(parseValidFilters(HistoryFilters, text)).toEqual(expected);
    });

    it.each([
        { text: "name:name is:published", expected: { name: "name" } },
        { text: "published:false name:name", expected: { name: "name" } },
        { text: "name:name invalid:invalid user:testUser", expected: { name: "name", user: "testUser" } },
    ])("parses published-workflow filters from '$text'", ({ text, expected }) => {
        expect(parseValidFilters(getWorkflowFilters("published"), text)).toEqual(expected);
    });
});

describe("filter text normalization retains unspecified text", () => {
    it.each([
        { name: "workflow tag with an unquoted multi-word value", text: "tag:amrfinderplus_report metagenomics" },
        { name: "workflow search without filter keys", text: "grep1" },
    ])("preserves $name", ({ text }) => {
        // Workflows have no autoFilterKey: with quoteStrings disabled, text up to
        // the next key belongs to the current value, including unquoted spaces.
        expect(validatedFilterText(getWorkflowFilters("my"), text)).toBe(text);
    });

    it.each([
        { name: "history list", filtering: getHistoryListFilters("my"), text: "grep1 tag:foo" },
        {
            name: "credentials list",
            filtering: new Filtering(
                {
                    name: { type: String, handler: contains("name"), menuItem: true },
                    tool: { type: String, handler: contains("tool"), menuItem: true },
                    service: { type: String, handler: contains("service"), menuItem: true },
                },
                undefined,
                true,
                "name",
            ),
            text: "grep1 tool:foo",
        },
        {
            name: "grid list",
            filtering: new Filtering(
                {
                    name: { type: String, handler: contains("name"), menuItem: true },
                    extension: { type: String, handler: contains("extension"), menuItem: true },
                },
                undefined,
                true,
                "name",
            ),
            text: "grep1 extension:txt",
        },
    ])("preserves search text alongside filters in $name", ({ filtering, text }) => {
        expect(validatedFilterText(filtering, text)).toBe(text);
        expect(validatedFilterText(filtering, "grep1")).toBe("grep1");
    });
});

describe("workflow parsing with quoteStrings disabled", () => {
    it.each([
        { name: "key:value tokens", text: "name:RNAseq tag:foo", expected: { name: "RNAseq", tag: ["foo"] } },
        { name: "quotes retained in a value", text: "name:'RNAseq'", expected: { name: "'RNAseq'" } },
        { name: "an unquoted multi-word value", text: "name:my workflow name", expected: { name: "my workflow name" } },
    ])("parses $name", ({ text, expected }) => {
        expect(Object.fromEntries(getWorkflowFilters("my").getFiltersForText(text))).toEqual(expected);
    });

    it.each(["name:RNAseq is:published", "tag:amrfinderplus_report metagenomics"])(
        "normalizes '%s' without changing it",
        (text) => {
            expect(validatedFilterText(getWorkflowFilters("my"), text)).toBe(text);
        },
    );
});

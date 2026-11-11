import { describe, expect, it, vi } from "vitest";
import { ref, shallowRef } from "vue";

import Filtering, { contains, equals } from "@/utils/filtering";

import { useFilterTextValidation } from "./filterTextValidation";

function nameFiltering() {
    return new Filtering({ name: { handler: contains("name"), menuItem: true } }, undefined, false, "name");
}

describe("useFilterTextValidation", () => {
    it("drops invalid filters from the query and flags them", () => {
        const filterText = ref("name:rna unknown:x");
        const { hasInvalidFilters, invalidFilters, validatedFilterText } = useFilterTextValidation(
            nameFiltering(),
            filterText,
        );

        expect(hasInvalidFilters.value).toBe(true);
        expect(Object.keys(invalidFilters.value ?? {})).toEqual(["unknown"]);
        expect(validatedFilterText()).toBe("name:rna");
    });

    it("takes quoted text as is, without its quotes", () => {
        const filterText = ref("'unknown:x name:rna'");
        const { hasInvalidFilters, validatedFilterText } = useFilterTextValidation(nameFiltering(), filterText);

        expect(hasInvalidFilters.value).toBe(false);
        expect(validatedFilterText()).toBe("unknown:x name:rna");
    });

    it.each([
        ["backend format by default", undefined, true],
        ["display format when asked", false, false],
    ])("builds the query from the typed text, in %s", (_, backendFormatted, expected) => {
        const filtering = nameFiltering();
        const getFilterText = vi.spyOn(filtering, "getFilterText");

        useFilterTextValidation(filtering, ref("name:rna"), backendFormatted).validatedFilterText();

        expect(getFilterText).toHaveBeenCalledWith({ name: "rna" }, expected, "name:rna");
    });

    it("follows a filter class that changes", () => {
        const filtering = shallowRef(nameFiltering());
        const filterText = ref("tag:x");
        const { hasInvalidFilters } = useFilterTextValidation(filtering, filterText);
        expect(hasInvalidFilters.value).toBe(true);

        filtering.value = new Filtering({ tag: { handler: equals("tag", "tag"), menuItem: true } }, undefined, false);

        expect(hasInvalidFilters.value).toBe(false);
    });

    it("works without a filter class", () => {
        const { hasInvalidFilters, validatedFilterText } = useFilterTextValidation(undefined, ref("anything"));

        expect(hasInvalidFilters.value).toBe(false);
        expect(validatedFilterText()).toBe("anything");
    });
});

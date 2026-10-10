import { getLocalVue, nth } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import { SINGULAR_DATA_URI, SINGULAR_FILE_URI, SINGULAR_LIST_URI } from "./testData/uriData";
import { type DataUri, isDataUriCollection, isDataUriCollectionElementCollection } from "./types";

import FormDataUri from "./FormDataUri.vue";

enableAutoUnmount(afterEach);

const SELECTORS = {
    file: "[data-description='uri element file']",
    collection: "[data-description='uri element collection']",
    location: "[data-description='uri location']",
    identifier: "[data-description='uri element identifier']",
};

function mountDataUri(value: DataUri) {
    // Render the recursive URI elements: their file labels and locations are the behavior under test.
    return mount(FormDataUri, { props: { value }, global: getLocalVue() });
}

describe("FormDataUri", () => {
    it.each([
        { name: "data", value: SINGULAR_DATA_URI, identifier: "Data" },
        { name: "file", value: SINGULAR_FILE_URI, identifier: "File" },
    ])("renders a singular $name URI with its default label and location", ({ value, identifier }) => {
        if (!("location" in value)) {
            throw new Error("The singular URI fixture must include a location");
        }
        const wrapper = mountDataUri(value);

        expect(wrapper.findAll(SELECTORS.file)).toHaveLength(1);
        expect(wrapper.find(SELECTORS.location).text()).toBe(value.location);
        expect(wrapper.find(SELECTORS.identifier).text()).toBe(identifier);
    });

    it("renders list elements in fixture order with their identifiers and locations", () => {
        if (!isDataUriCollection(SINGULAR_LIST_URI)) {
            throw new Error("The list URI fixture must be a collection");
        }
        const wrapper = mountDataUri(SINGULAR_LIST_URI);
        const files = wrapper.findAll(SELECTORS.file);

        expect(wrapper.findAll(SELECTORS.collection)).toHaveLength(1);
        expect(files).toHaveLength(SINGULAR_LIST_URI.elements.length);
        SINGULAR_LIST_URI.elements.forEach((expected, index) => {
            expect(isDataUriCollectionElementCollection(expected)).toBe(false);
            if (isDataUriCollectionElementCollection(expected)) {
                throw new Error("The list URI fixture must contain files");
            }
            const file = nth(files, index);
            expect(file.find(SELECTORS.location).text()).toBe(expected.location);
            expect(file.find(SELECTORS.identifier).text()).toBe(expected.identifier);
        });
    });
});

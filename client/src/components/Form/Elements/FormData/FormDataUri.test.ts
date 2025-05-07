import { mount, type Wrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";

import { SINGULAR_DATA_URI, SINGULAR_FILE_URI, SINGULAR_LIST_URI } from "./testData/uriData";
import { type DataUri, type DataUriCollectionElement, isDataUriCollectionElementCollection } from "./types";

import FormDataUri from "./FormDataUri.vue";

const SELECTORS = {
    URI_ELEMENT_FILE: "[data-description='uri element file']",
    URI_ELEMENT_COLLECTION: "[data-description='uri element collection']",
    URI_LOCATION: "[data-description='uri location']",
    URI_IDENTIFIER: "[data-description='uri element identifier']",
    URI_ELEMENT_EXT: "[data-description='uri element ext']",
};

function initWrapper(value: DataUri) {
    const wrapper = mount(FormDataUri as object, {
        propsData: {
            value,
        },
    });
    flushPromises();
    return wrapper;
}

function assertLocationIsFound(wrapper: Wrapper<Vue>, uriData: DataUri | DataUriCollectionElement) {
    if (!("location" in uriData)) {
        throw new Error("The DataUri type does not have a url property");
    }

    expect(wrapper.find(SELECTORS.URI_LOCATION).text()).toBe(uriData.location);
}

function assertIdentifierIsFound(
    wrapper: Wrapper<Vue>,
    uriData: DataUri | DataUriCollectionElement,
    hasIdentifier = false,
    expectIdentifier = "File"
) {
    if (hasIdentifier) {
        if (!("identifier" in uriData)) {
            throw new Error("The DataUri type is not a DataUriCollectionElement");
        }
        expect(wrapper.find(SELECTORS.URI_IDENTIFIER).text()).toBe((uriData as DataUriCollectionElement).identifier);
    } else {
        expect(wrapper.find(SELECTORS.URI_IDENTIFIER).text()).toBe(expectIdentifier);
    }
}

describe("FormDataUri", () => {
    it("renders a singular data input correctly", () => {
        const wrapper = initWrapper(SINGULAR_DATA_URI);
        expect(wrapper.findAll(SELECTORS.URI_ELEMENT_FILE).length).toBe(1);

        assertLocationIsFound(wrapper, SINGULAR_DATA_URI);
        assertIdentifierIsFound(wrapper, SINGULAR_DATA_URI, false, "Data");
    });

    it("renders a singular file input correctly", () => {
        const wrapper = initWrapper(SINGULAR_FILE_URI);
        expect(wrapper.findAll(SELECTORS.URI_ELEMENT_FILE).length).toBe(1);

        assertLocationIsFound(wrapper, SINGULAR_FILE_URI);
        assertIdentifierIsFound(wrapper, SINGULAR_FILE_URI);
    });

    it("renders a singular list input correctly", () => {
        const testUriDataCollection = SINGULAR_LIST_URI;

        const wrapper = initWrapper(testUriDataCollection);

        if (!("elements" in testUriDataCollection)) {
            throw new Error("The `DataUri` type is not `DataUriCollection`");
        }
        expect(wrapper.findAll(SELECTORS.URI_ELEMENT_COLLECTION).length).toBe(1);

        const collectionElements = wrapper.findAll(SELECTORS.URI_ELEMENT_FILE);
        expect(collectionElements.length).toBe(testUriDataCollection.elements.length);

        for (let i = 0; i < collectionElements.length; i++) {
            const element = collectionElements.at(i);
            const expectedElement = testUriDataCollection.elements[i];
            if (!expectedElement) {
                throw new Error("No element found");
            }

            expect(isDataUriCollectionElementCollection(expectedElement)).toBe(false);

            assertLocationIsFound(element, expectedElement);

            assertIdentifierIsFound(element, expectedElement, true);
        }
    });
});

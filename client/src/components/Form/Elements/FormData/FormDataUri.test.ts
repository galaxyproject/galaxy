import { mount, type Wrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";

import {
    SINGULAR_DATA_URI,
    SINGULAR_FILE_URI,
    SINGULAR_FILE_URI_ALIAS,
    SINGULAR_LIST_URI,
    SINGULAR_LIST_URI_ALIAS,
} from "./testData/uriData";
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

function assertLocationIsFound(
    wrapper: Wrapper<Vue>,
    uriData: DataUri | DataUriCollectionElement,
    locationKey = "url"
) {
    if (!(locationKey in uriData)) {
        throw new Error(
            `The DataUri type is not DataUriData, or is expected to have the wrong location key: "${locationKey}"`
        );
    }

    expect(wrapper.find(SELECTORS.URI_LOCATION).text()).toBe(uriData[locationKey as keyof typeof uriData]);
}

function assertIdentifierIsFound(
    wrapper: Wrapper<Vue>,
    uriData: DataUri | DataUriCollectionElement,
    hasIdentifier = false,
    expectIdentifier = "Dataset"
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

function assertUriDataCollectionValues(wrapper: Wrapper<Vue>, testUriDataCollection: DataUri, locationKey = "url") {
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

        assertLocationIsFound(element, expectedElement, locationKey);

        assertIdentifierIsFound(element, expectedElement, true);
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

        assertLocationIsFound(wrapper, SINGULAR_FILE_URI, "location");
        assertIdentifierIsFound(wrapper, SINGULAR_FILE_URI);
    });

    it("renders a singular file input correctly with alias", () => {
        const wrapper = initWrapper(SINGULAR_FILE_URI_ALIAS);
        expect(wrapper.findAll(SELECTORS.URI_ELEMENT_FILE).length).toBe(1);

        assertLocationIsFound(wrapper, SINGULAR_FILE_URI_ALIAS);
        assertIdentifierIsFound(wrapper, SINGULAR_FILE_URI_ALIAS);
    });

    it("renders a singular list input correctly", () => {
        const testUriData = SINGULAR_LIST_URI;

        const wrapper = initWrapper(testUriData);

        assertUriDataCollectionValues(wrapper, testUriData, "location");
    });

    it("renders a singular list input correctly with alias", () => {
        const testUriData = SINGULAR_LIST_URI_ALIAS;

        const wrapper = initWrapper(testUriData);

        assertUriDataCollectionValues(wrapper, testUriData);
    });
});

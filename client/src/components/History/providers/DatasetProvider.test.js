/**
 * The collection API for a collection does not, on its own, return enough data about a dataset
 * collection to properly render all the requested features for a nested dataset. This provder
 * allows the UI to request and cache a fresh version from the server on-demand as the user expands
 * the dataset (that is cantained in a collection).
 *
 * Sometimes the same dataset will be present in the cache because it was hidden to create a
 * collection, sowe check the cache first before querying.
 *
 * NOTE: this is not needed for datasets at the root level of a history. The full set of information
 * is already present in history content query at that level, or in any other scenario where the
 * entire dataset field set has been returned.
 *
 * Sample Usage:
 *
 * <DatasetProvider :item="collectionData" v-slot="{ dataset, load, loaded }">
 *     <YourCustomUI v-if="loaded" :dataset="dataset" />
 *     <spn v-else>Loading...</spn>
 * </DatasetProvider>
 */

import { shallowMount } from "@vue/test-utils";
import { getLocalVue, waitForLifecyleEvent } from "jest/helpers";
import { wipeDatabase } from "../caching";
import { getContentDetails } from "../model/queries";

// test me
import { datasetContentValidator, default as DatasetProvider } from "./DatasetProvider";

//#region Mocking

jest.mock("app");
jest.mock("../caching");
jest.mock("../model/queries");

beforeEach(wipeDatabase);
afterEach(wipeDatabase);

const fakeDataset = { history_id: 123, type_id: "abc" };

getContentDetails.mockImplementation(async (id) => {
    return fakeDataset;
});

//#endregion

describe("DatasetProvider component", () => {
    // Test the prop validator
    describe("prop validation function", () => {
        it("should require a history_id and a type_id at a minimum", () => {
            expect(datasetContentValidator({})).toBe(false);
            expect(datasetContentValidator({ history_id: 123 })).toBe(false);
            expect(datasetContentValidator({ type_id: "abc123" })).toBe(false);
            expect(datasetContentValidator({ history_id: 123, type_id: "abc123" })).toBe(false);
            expect(datasetContentValidator({ history_id: 123, type_id: "abc123", id: "sdfasdf" })).toBe(false);
            expect(
                datasetContentValidator({
                    history_id: 123,
                    type_id: "abc123",
                    id: "sdfasdf",
                    history_content_type: "dataset",
                })
            ).toBe(true);
        });
    });

    describe("DatasetProvider", () => {
        let wrapper;
        let slotProps;

        beforeEach(async () => {
            const propsData = { item: fakeDataset };
            const localVue = getLocalVue();

            wrapper = shallowMount(DatasetProvider, {
                localVue,
                propsData,
                scopedSlots: {
                    default(props) {
                        slotProps = props;
                    },
                },
            });

            await waitForLifecyleEvent(wrapper.vm, "updated");
        });

        xtest("initial load should have abbreviated dataset object created from collection item data", () => {
            expect(slotProps.dataset).toBeDefined();
        });

        xtest("when user requests detailed version, lookup and return full dataset object", () => {
            expect(slotProps.dataset).toBeDefined();
        });
    });
});

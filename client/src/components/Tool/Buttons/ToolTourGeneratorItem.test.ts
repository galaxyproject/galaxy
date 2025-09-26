import { getLocalVue } from "@tests/jest/helpers";
import { mount, type Wrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia, defineStore, setActivePinia } from "pinia";
import { ref } from "vue";

import { useServerMock } from "@/api/client/__mocks__";
import type { State } from "@/components/History/Content/model/states";
import TEST_TOUR from "@/components/Tour/sampleTour.json";

import ToolTourGeneratorItem from "./ToolTourGeneratorItem.vue";

const TEST_TOOL_ID = "test-tool-id";
const TEST_TOOL_VERSION = "1.0";
const TEST_HISTORY_ID = "test-history-id";

const { server, http } = useServerMock();

// Mock the 3 stores used in the component
jest.mock("@/stores/historyStore", () => {
    return {
        useHistoryStore: () =>
            defineStore("history", {
                state: () => ({
                    currentHistoryId: TEST_HISTORY_ID,
                }),
            })(),
    };
});
let mockedHistoryItemsStore: ReturnType<ReturnType<typeof defineStore>>;
jest.mock("@/stores/historyItemsStore", () => {
    return {
        useHistoryItemsStore: () => mockedHistoryItemsStore,
    };
});
const setTourMock = jest.fn();
jest.mock("@/stores/tourStore", () => {
    return {
        useTourStore: () =>
            defineStore("tour", {
                state: () => ({
                    toolGeneratedTours: {},
                }),
                actions: {
                    setTour: setTourMock,
                },
            })(),
    };
});

// Mock the toast composable to track the messages
const toastMock = jest.fn((message, type: "success" | "info" | "error") => {
    return { message, type };
});
jest.mock("@/composables/toast", () => ({
    Toast: {
        success: jest.fn().mockImplementation((message) => {
            toastMock(message, "success");
        }),
        info: jest.fn().mockImplementation((message) => {
            toastMock(message, "info");
        }),
        error: jest.fn().mockImplementation((message) => {
            toastMock(message, "error");
        }),
    },
}));

describe("Tool Generated Tour Dropdown Item", () => {
    let wrapper: Wrapper<Vue>;
    /** This is used to trigger a change in what `historyItemsStore.getStatesForHids` returns */
    const currentItemState = ref<State | null>(null);

    beforeEach(async () => {
        setActivePinia(createPinia());
        mockedHistoryItemsStore = defineStore("historyItems", {
            getters: {
                // If `hids` are provided, return the `currentItemState` for each hid
                getStatesForHids: () => (_: string, hids: number[]) => {
                    if (currentItemState.value === null) {
                        return {};
                    }
                    const entries = hids.map((hid) => [hid, currentItemState.value]);
                    return Object.fromEntries(entries) as Record<string, State>;
                },
            },
        })();

        wrapper = mount(ToolTourGeneratorItem as object, {
            propsData: {
                toolId: TEST_TOOL_ID,
                toolVersion: TEST_TOOL_VERSION,
            },
            localVue: getLocalVue(),
            stubs: {
                FontAwesomeIcon: true,
            },
        });
    });

    afterEach(() => {
        wrapper.destroy();
        server.resetHandlers();
        currentItemState.value = null;
    });

    it("generates a basic tour (that doesn't wait on datasets) on click", async () => {
        server.use(
            http.get("/api/tours/generate", ({ response }) => {
                return response(200).json({
                    tour: TEST_TOUR,
                    uploaded_hids: [],
                    use_datasets: false,
                });
            }),
        );

        const dropdownItem = await clickDropdownItem();

        // Since there is nothing to wait for the tour is ready and in the store
        tourHasGenerated(dropdownItem);

        // Only a singular toast confirming the tour is ready
        expect(toastMock).toHaveBeenCalledTimes(1);
    });

    it("generates a tour that that waits for datasets to be ok", async () => {
        server.use(
            http.get("/api/tours/generate", ({ response }) => {
                return response(200).json({
                    tour: TEST_TOUR,
                    uploaded_hids: [1, 2, 3],
                    use_datasets: true,
                });
            }),
        );

        const dropdownItem = await clickDropdownItem();

        // Unlike the tour without datasets, the tour is still generating after local state update
        tourIsGenerating(dropdownItem);

        // Confirm that there is a toast
        expect(toastMock).toHaveBeenCalledWith("This tour waits for history datasets to be ready.", "info");

        // Now we mock history items going through states, and the tour generation completing only when all are ok

        await mockItemsState("new");
        tourIsGenerating(dropdownItem);

        await mockItemsState("running");
        tourIsGenerating(dropdownItem);

        await mockItemsState("ok");
        tourHasGenerated(dropdownItem);

        // We know by now this is the 2nd toast
        expect(toastMock).toHaveBeenCalledTimes(2);
    });

    it("generates a tour that that uploads datasets but they become invalid", async () => {
        server.use(
            http.get("/api/tours/generate", ({ response }) => {
                return response(200).json({
                    tour: TEST_TOUR,
                    uploaded_hids: [1, 2, 3],
                    use_datasets: true,
                });
            }),
        );

        const dropdownItem = await clickDropdownItem();

        // Now we mock history items going through states, and the tour generation failing when one is invalid

        await mockItemsState("new");
        tourIsGenerating(dropdownItem);

        await mockItemsState("running");
        tourIsGenerating(dropdownItem);

        await mockItemsState("error");
        tourGenerationFailedWith(
            dropdownItem,
            "This tour uploads datasets that failed to be created. You can try generating the tour again.",
        );

        // We know by now this is the 2nd toast
        expect(toastMock).toHaveBeenCalledTimes(2);
    });

    // LOCAL METHODS: ----------------------------------------------------------------------

    /** Finds and confirms the tool generated tour dropdown item exists, and clicks it. */
    async function clickDropdownItem() {
        const dropdownItem = wrapper.find("[data-description='click to generate tour']");
        expect(dropdownItem.exists()).toBe(true);

        await dropdownItem.trigger("click");

        tourIsGenerating(dropdownItem);

        // Flush after tour generation API call, which updates the local state
        await flushPromises();

        return dropdownItem;
    }

    /** By simply setting the local `currentItemState` ref, we mock the `historyItemsStore` getter to
     * return the desired state for `uploaded_hids` as returned by the tour generation API. */
    async function mockItemsState(state: State) {
        currentItemState.value = state;
        await flushPromises();
    }

    /** Confirms the tour is _(still)_ generating, given that the dropdown item is disabled
     * and the tour store not yet updated. */
    function tourIsGenerating(dropdownItem: Wrapper<Vue>) {
        expect(dropdownItem.attributes("aria-disabled")).toBe("true");
        expect(setTourMock).toHaveBeenCalledTimes(0);
    }

    /** Confirms the tour has been generated and the `tourStore` updated with it. */
    function tourHasGenerated(dropdownItem: Wrapper<Vue>) {
        // The second toast confirms the tour is ready
        expect(toastMock).toHaveBeenCalledWith("You can now start the tour", "success");
        expect(dropdownItem.attributes("aria-disabled")).toBeUndefined();

        // The tour is now in the store, with the expected key
        expect(setTourMock).toHaveBeenCalledWith(`tool-generated-${TEST_TOOL_ID}-${TEST_TOOL_VERSION}`);
    }

    /** Confirms the tour generation failed, the dropdown item is enabled, the tour store not updated
     * and the expected error is message shown in a toast.
     */
    function tourGenerationFailedWith(dropdownItem: Wrapper<Vue>, message: string) {
        // The second toast confirms the tour generation failed
        expect(toastMock).toHaveBeenCalledWith(message, "error");
        expect(dropdownItem.attributes("aria-disabled")).toBeUndefined();
        expect(setTourMock).toHaveBeenCalledTimes(0);
    }
});

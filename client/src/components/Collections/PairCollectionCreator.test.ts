import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { HDASummary } from "@/api";
import { useServerMock } from "@/api/client/__mocks__";
import { Toast } from "@/composables/toast";

import FixedIdentifierDatasetCollectionElementView from "./FixedIdentifierDatasetCollectionElementView.vue";
import DatasetCollectionElementView from "./ListDatasetCollectionElementView.vue";
import PairCollectionCreator from "./PairCollectionCreator.vue";

vi.mock("@/composables/toast");

const toastError = vi.mocked(Toast.error);

const localVue = getLocalVue(true);

const { server, http } = useServerMock();
beforeEach(() => {
    vi.clearAllMocks();
    server.use(
        http.get("/api/configuration", ({ response }) => response(200).json({})),
        http.get("/api/genomes", ({ response }) => response(200).json([])),
    );
});

function buildFakeDataset(id: string, hid: number, name: string, overrides: object = {}): HDASummary {
    return {
        id,
        hid,
        name,
        history_content_type: "dataset",
        deleted: false,
        purged: false,
        visible: true,
        state: "ok",
        extension: "txt",
        history_id: "history-1",
        ...overrides,
    } as unknown as HDASummary;
}

async function mountCreator(initialElements: HDASummary[]) {
    const pinia = createTestingPinia({ createSpy: vi.fn });
    setActivePinia(pinia);

    const wrapper = mount(PairCollectionCreator as object, {
        propsData: {
            historyId: "history-1",
            initialElements,
            mode: "modal",
        },
        localVue,
        pinia,
        stubs: {
            DefaultBox: true,
        },
    });

    await flushPromises();
    return wrapper;
}

/** The forward/reverse slots as ids - an empty slot renders no view at all. */
function pairedIds(wrapper: ReturnType<typeof mount>): string[] {
    return wrapper
        .findAllComponents(FixedIdentifierDatasetCollectionElementView)
        .wrappers.map((slot) => (slot.props("element") as HDASummary).id);
}

async function clickDataset(wrapper: ReturnType<typeof mount>, id: string) {
    const view = wrapper
        .findAllComponents(DatasetCollectionElementView)
        .wrappers.find((candidate) => (candidate.props("element") as HDASummary).id === id);
    view?.vm.$emit("element-is-selected", view.props("element"));
    await flushPromises();
}

describe("PairCollectionCreator", () => {
    it("keeps both sides of the pair when initialElements changes", async () => {
        const wrapper = await mountCreator([buildFakeDataset("a", 1, "one"), buildFakeDataset("b", 2, "two")]);

        await clickDataset(wrapper, "a");
        await clickDataset(wrapper, "b");
        expect(pairedIds(wrapper)).toEqual(["a", "b"]);

        // same datasets, new prop identity (e.g. a history poll tick)
        await wrapper.setProps({ initialElements: [buildFakeDataset("a", 1, "one"), buildFakeDataset("b", 2, "two")] });
        await flushPromises();

        expect(pairedIds(wrapper)).toEqual(["a", "b"]);
        expect(toastError).not.toHaveBeenCalled();
    });

    it("empties the slot whose dataset left the history and says it was removed", async () => {
        const a = buildFakeDataset("a", 1, "one");
        const wrapper = await mountCreator([a, buildFakeDataset("b", 2, "two")]);

        await clickDataset(wrapper, "a");
        await clickDataset(wrapper, "b");

        await wrapper.setProps({ initialElements: [a] });
        await flushPromises();

        expect(pairedIds(wrapper)).toEqual(["a"]);
        expect(toastError).toHaveBeenCalledTimes(1);
        expect(toastError).toHaveBeenCalledWith("2: two has been removed from the collection", "Invalid element");
    });

    it("empties the slot whose dataset is no longer usable and says why", async () => {
        const a = buildFakeDataset("a", 1, "one");
        const wrapper = await mountCreator([a, buildFakeDataset("b", 2, "two")]);

        await clickDataset(wrapper, "a");
        await clickDataset(wrapper, "b");

        await wrapper.setProps({ initialElements: [a, buildFakeDataset("b", 2, "two", { state: "error" })] });
        await flushPromises();

        expect(pairedIds(wrapper)).toEqual(["a"]);
        expect(toastError).toHaveBeenCalledTimes(1);
        expect(toastError).toHaveBeenCalledWith(
            "2: two has errored, is paused, or is not accessible and is not a valid element for this collection",
            "Invalid element",
        );
    });
});

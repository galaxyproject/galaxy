import "@/components/Form/Elements/FormSelectMany/worker/__mocks__/selectMany";

import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { HDASummary } from "@/api";
import { useServerMock } from "@/api/client/__mocks__";
import { Toast } from "@/composables/toast";

import ListCollectionCreator from "./ListCollectionCreator.vue";
import FormSelectMany from "@/components/Form/Elements/FormSelectMany/FormSelectMany.vue";

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

    const wrapper = mount(ListCollectionCreator as object, {
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

function inListElements(wrapper: ReturnType<typeof mount>): HDASummary[] {
    return wrapper.findComponent(FormSelectMany).props("value") as HDASummary[];
}

async function selectIntoList(wrapper: ReturnType<typeof mount>, names: string[]) {
    for (const name of names) {
        const option = wrapper
            .findAll(".options-list.unselected > button")
            .wrappers.find((candidate) => candidate.text().includes(name));
        await option?.trigger("click");
        await flushPromises();
    }
}

describe("ListCollectionCreator", () => {
    it("keeps the user's list when initialElements changes, re-projected onto the rebuilt elements", async () => {
        const wrapper = await mountCreator([buildFakeDataset("a", 1, "one"), buildFakeDataset("b", 2, "two")]);

        await selectIntoList(wrapper, ["two", "one"]);
        expect(inListElements(wrapper).map((element) => element.id)).toEqual(["b", "a"]);

        // same datasets, new prop identity (e.g. a history poll tick)
        const refreshed = [buildFakeDataset("a", 1, "one"), buildFakeDataset("b", 2, "two")];
        await wrapper.setProps({ initialElements: refreshed });
        await flushPromises();

        // the user's order survives, holding the creator's working copies rather than the props
        expect(inListElements(wrapper).map((element) => element.id)).toEqual(["b", "a"]);
        expect(inListElements(wrapper)[0]).not.toBe(refreshed[1]);
        expect(toastError).not.toHaveBeenCalled();
    });

    it("drops a dataset that left the history and says it was removed from the collection", async () => {
        const a = buildFakeDataset("a", 1, "one");
        const wrapper = await mountCreator([a, buildFakeDataset("b", 2, "two")]);

        await selectIntoList(wrapper, ["one", "two"]);

        await wrapper.setProps({ initialElements: [a] });
        await flushPromises();

        expect(inListElements(wrapper).map((element) => element.id)).toEqual(["a"]);
        expect(toastError).toHaveBeenCalledTimes(1);
        expect(toastError).toHaveBeenCalledWith("2: two has been removed from the collection", "Invalid element");
    });

    it("drops a dataset that is still there but no longer usable and says why", async () => {
        const a = buildFakeDataset("a", 1, "one");
        const wrapper = await mountCreator([a, buildFakeDataset("b", 2, "two")]);

        await selectIntoList(wrapper, ["one", "two"]);

        await wrapper.setProps({ initialElements: [a, buildFakeDataset("b", 2, "two", { state: "error" })] });
        await flushPromises();

        expect(inListElements(wrapper).map((element) => element.id)).toEqual(["a"]);
        expect(toastError).toHaveBeenCalledTimes(1);
        expect(toastError).toHaveBeenCalledWith(
            "2: two has errored, is paused, or is not accessible and is not a valid element for this collection",
            "Invalid element",
        );
    });
});

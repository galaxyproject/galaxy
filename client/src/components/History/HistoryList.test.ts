import { createTestingPinia } from "@pinia/testing";
import { getFakeRegisteredUser } from "@tests/test-data";
import { getLocalVue, suppressBootstrapVueWarnings } from "@tests/vitest/helpers";
import type { Mock } from "@vitest/spy";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import VueRouter from "vue-router";

import { getMyHistories } from "@/api/histories";
import { useUserStore } from "@/stores/userStore";

import HistoryCardList from "./HistoryCardList.vue";
import HistoryList from "./HistoryList.vue";

vi.mock("@/api/histories");

const localVue = getLocalVue();
localVue.use(VueRouter);
const router = new VueRouter();

const mockGetMyHistories = getMyHistories as Mock;

type HistoriesResponse = { data: { id: string; name: string }[]; total: number };

function historiesResponse(names: string[]): HistoriesResponse {
    return { data: names.map((name) => ({ id: name, name })), total: names.length };
}

function deferred() {
    let resolve!: (value: HistoriesResponse) => void;
    const promise = new Promise<HistoriesResponse>((r) => {
        resolve = r;
    });
    return { promise, resolve };
}

async function mountHistoryList() {
    const pinia = createTestingPinia({ createSpy: vi.fn });
    setActivePinia(pinia);
    const userStore = useUserStore();
    userStore.currentUser = getFakeRegisteredUser();

    const wrapper = mount(HistoryList as object, {
        localVue,
        pinia,
        router,
        stubs: { HistoryCardList: true },
    });
    await flushPromises();
    return wrapper;
}

async function clickSortByNameTwice(wrapper: ReturnType<typeof mount>) {
    const descending = deferred();
    const ascending = deferred();
    mockGetMyHistories.mockReturnValueOnce(descending.promise).mockReturnValueOnce(ascending.promise);

    await wrapper.find("#sortby-name").trigger("click");
    await wrapper.find("#sortby-name").trigger("click");

    expect(mockGetMyHistories).toHaveBeenNthCalledWith(2, expect.objectContaining({ sortBy: "name", sortDesc: true }));
    expect(mockGetMyHistories).toHaveBeenNthCalledWith(3, expect.objectContaining({ sortBy: "name", sortDesc: false }));
    return { descending, ascending };
}

function listedNames(wrapper: ReturnType<typeof mount>) {
    return wrapper
        .findComponent(HistoryCardList)
        .props("histories")
        .map((history: { name: string }) => history.name);
}

function isBusy(wrapper: ReturnType<typeof mount>) {
    return wrapper.find("#history-list-overlay").attributes("aria-busy") === "true";
}

describe("HistoryList", () => {
    beforeEach(() => {
        suppressBootstrapVueWarnings();
        mockGetMyHistories.mockReset();
        mockGetMyHistories.mockResolvedValueOnce(historiesResponse(["b", "a"]));
    });

    it("ignores a superseded sort response that arrives last", async () => {
        const wrapper = await mountHistoryList();
        const { descending, ascending } = await clickSortByNameTwice(wrapper);

        ascending.resolve(historiesResponse(["a", "b"]));
        await flushPromises();
        descending.resolve(historiesResponse(["b", "a"]));
        await flushPromises();

        expect(listedNames(wrapper)).toEqual(["a", "b"]);
        expect(isBusy(wrapper)).toBe(false);
    });

    it("stays busy until the latest sort response arrives", async () => {
        const wrapper = await mountHistoryList();
        const { descending, ascending } = await clickSortByNameTwice(wrapper);

        descending.resolve(historiesResponse(["b", "a"]));
        await flushPromises();

        expect(isBusy(wrapper)).toBe(true);

        ascending.resolve(historiesResponse(["a", "b"]));
        await flushPromises();

        expect(listedNames(wrapper)).toEqual(["a", "b"]);
        expect(isBusy(wrapper)).toBe(false);
    });
});

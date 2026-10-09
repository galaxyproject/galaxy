import { getFakeHistorySummary, getFakeRegisteredUser } from "@tests/test-data";
import { emittedArg, getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia } from "pinia";
import { afterEach, describe, expect, it } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import { useHistoryStore } from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";

import SelectorModal from "./SelectorModal.vue";
import GCard from "@/components/Common/GCard.vue";

enableAutoUnmount(afterEach);
const CURRENT_HISTORY_ID = "COOL_ID";
const { server, http } = useServerMock();

async function mountSelector(props = {}) {
    const allHistories = Array.from({ length: 15 }, (_, index) =>
        getFakeHistorySummary({
            id: index === 0 ? CURRENT_HISTORY_ID : `ID-${index}`,
            name: `History-${index}`,
        }),
    );
    server.use(
        http.get("/api/histories", ({ response, query }) => {
            const offset = Number(query.get("offset")) || 0;
            const limit = Number(query.get("limit")) || 10;
            return response(200).json(allHistories.slice(offset, offset + limit));
        }),
        http.get("/api/histories/count", ({ response }) => response(200).json(allHistories.length)),
    );

    const pinia = createPinia();
    const global = withPlugins(getLocalVue(), pinia);
    useUserStore(pinia).setCurrentUser(getFakeRegisteredUser({ email: "email", id: "user_id", total_disk_usage: 0 }));
    const historyStore = useHistoryStore(pinia);
    await historyStore.loadHistories();
    historyStore.setCurrentHistoryId(CURRENT_HISTORY_ID);
    const wrapper = mount(SelectorModal, {
        props: { histories: historyStore.histories, showModal: true, ...props },
        global,
    });
    await flushPromises();
    return wrapper;
}

describe("History SelectorModal", () => {
    it("marks the current history in the list", async () => {
        const wrapper = await mountSelector();

        expect(wrapper.get(`[data-pk="${CURRENT_HISTORY_ID}"]`).classes()).toContain("g-card-current");
    });

    it("loads the remaining histories when Load More is clicked", async () => {
        const wrapper = await mountSelector();
        expect(wrapper.findAllComponents(GCard)).toHaveLength(10);
        const loadMore = wrapper.get("[data-description='load more items button']");

        await loadMore.trigger("click");
        await flushPromises();

        expect(wrapper.findAllComponents(GCard)).toHaveLength(15);
        expect(wrapper.find("[data-description='load more items button']").exists()).toBe(false);
    });

    it("emits the clicked history in single-selection mode", async () => {
        const wrapper = await mountSelector();
        expect(wrapper.emitted("selectHistory")).toBeUndefined();

        await wrapper.get('[data-pk="ID-2"]').trigger("click");

        expect(wrapper.emitted("selectHistory")).toHaveLength(1);
        expect(emittedArg(wrapper, "selectHistory").id).toBe("ID-2");
    });

    it("shows the supplied selection instruction", async () => {
        const wrapper = await mountSelector({ selectionInstruction: "Click a history to copy datasets" });

        expect(wrapper.text()).toContain("Click a history to copy datasets");
    });

    it("emits both selected histories when multi-selection is confirmed", async () => {
        const wrapper = await mountSelector({ multiple: true });
        expect(wrapper.emitted("selectHistories")).toBeUndefined();

        await wrapper.get('[data-pk="ID-1"]').trigger("click");
        await wrapper.get('[data-pk="ID-2"]').trigger("click");

        expect(wrapper.findAll(".g-card-selected")).toHaveLength(2);
        await wrapper.get("[data-description='change selected histories button']").trigger("click");
        expect(wrapper.emitted("selectHistories")).toEqual([[[{ id: "ID-1" }, { id: "ID-2" }]]]);
    });
});

import { getFakeRegisteredUser } from "@tests/test-data";
import { mount } from "@vue/test-utils";
import { BListGroupItem } from "bootstrap-vue";
import flushPromises from "flush-promises";
import { createPinia } from "pinia";
import { getLocalVue } from "tests/jest/helpers";

import { useServerMock } from "@/api/client/__mocks__";
import { useHistoryStore } from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";

import SelectorModal from "./SelectorModal.vue";

const localVue = getLocalVue();

const CURRENT_HISTORY_ID = "COOL_ID";
const getFakeHistorySummaries = (num, selectedIndex = 0) => {
    const result = Array.from({ length: num }, (_, index) => ({
        id: index === selectedIndex ? CURRENT_HISTORY_ID : `ID-${index}`,
        name: `History-${index}`,
        tags: [],
        update_time: new Date().toISOString(),
    }));

    return result;
};
const PROPS_FOR_MODAL = {
    currentHistoryId: CURRENT_HISTORY_ID,
    histories: [],
    static: true, // Force the modal visible for testing
    showModal: true,
};
const PROPS_FOR_MODAL_MULTIPLE_SELECT = {
    ...PROPS_FOR_MODAL,
    multiple: true,
};

const CURRENT_HISTORY_INDICATION_TEXT = "(Current)";

const CURRENT_USER = {
    email: "email",
    id: "user_id",
    total_disk_usage: 0,
};

const { server, http } = useServerMock();

describe("History SelectorModal.vue", () => {
    let wrapper;
    let historyStore;
    const allHistories = getFakeHistorySummaries(15);

    async function mountWith(props) {
        server.use(
            http.get("/api/histories", ({ response, query }) => {
                const offset = Number(query.get("offset")) ?? 0;
                const limit = Number(query.get("limit")) ?? 10;
                return response(200).json(allHistories.slice(offset, offset + limit));
            }),
            http.get("/api/histories/count", ({ response }) => {
                return response(200).json(allHistories.length);
            })
        );

        const pinia = createPinia();
        wrapper = mount(SelectorModal, {
            propsData: props,
            localVue,
            pinia,
            stubs: {
                icon: { template: "<div></div>" },
            },
        });

        const userStore = useUserStore();
        userStore.setCurrentUser(getFakeRegisteredUser(CURRENT_USER));

        historyStore = useHistoryStore();
        await historyStore.loadHistories();
        await wrapper.setProps({
            histories: historyStore.histories,
        });
        historyStore.setCurrentHistoryId(props.currentHistoryId);

        await flushPromises();
    }

    it("should indicate the currently selected history", async () => {
        await mountWith(PROPS_FOR_MODAL);

        const currentHistoryRow = wrapper.find(`[data-pk="${CURRENT_HISTORY_ID}"]`);
        expect(currentHistoryRow.html()).toContain(CURRENT_HISTORY_INDICATION_TEXT);
    });

    it("paginates the histories", async () => {
        await mountWith(PROPS_FOR_MODAL);

        let displayedRows = wrapper.findAllComponents(BListGroupItem).wrappers;
        expect(displayedRows.length).toBe(10);
        expect(wrapper.find("[data-description='load more histories button']").exists()).toBe(true);

        await historyStore.loadHistories();
        await wrapper.setProps({
            histories: historyStore.histories,
        });

        displayedRows = wrapper.findAllComponents(BListGroupItem).wrappers;
        expect(displayedRows.length).toBe(15);
        expect(wrapper.find("[data-description='load more histories button']").exists()).toBe(false);
    });

    it("emits selectHistory with the correct history ID when a row is clicked", async () => {
        await mountWith(PROPS_FOR_MODAL);

        expect(wrapper.emitted()["selectHistory"]).toBeUndefined();

        const targetHistoryId = "ID-2";
        const targetRow = wrapper.find(`[data-pk="${targetHistoryId}"]`);
        await targetRow.trigger("click");

        expect(wrapper.emitted()["selectHistory"]).toBeDefined();
        expect(wrapper.emitted()["selectHistory"][0][0].id).toBe(targetHistoryId);
    });

    describe("Multi-selection Mode", () => {
        it("should select multiple histories", async () => {
            await mountWith(PROPS_FOR_MODAL_MULTIPLE_SELECT);

            expect(wrapper.emitted()["selectHistories"]).toBeUndefined();

            const targetHistoryId1 = "ID-1";
            const targetRow1 = wrapper.find(`[data-pk="${targetHistoryId1}"]`);
            await targetRow1.trigger("click");

            const targetHistoryId2 = "ID-2";
            const targetRow2 = wrapper.find(`[data-pk="${targetHistoryId2}"]`);
            await targetRow2.trigger("click");

            const selectedHistories = wrapper.findAll(".list-group-item.active").wrappers;
            expect(selectedHistories.length).toBe(2);

            const button = wrapper.find("[data-description='change selected histories button']");

            await button.trigger("click");

            expect(wrapper.emitted()["selectHistories"][0][0][0].id).toBe(targetHistoryId1);
        });
    });
});

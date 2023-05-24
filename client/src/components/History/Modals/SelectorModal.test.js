import MockAdapter from "axios-mock-adapter";
import axios from "axios";
import { createPinia } from "pinia";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import SelectorModal from "./SelectorModal";
import { getLocalVue } from "tests/jest/helpers";
import { useHistoryStore } from "stores/historyStore";
import { BListGroupItem } from "bootstrap-vue";

const localVue = getLocalVue();

const CURRENT_HISTORY_ID = "COOL_ID";
const getFakeHistorySummaries = (num, selectedIndex = 0) => {
    const result = Array.from({ length: num }, (_, index) => ({
        id: `ID-${index}`,
        name: `History-${index}`,
        tags: [],
        update_time: new Date().toISOString(),
    }));
    result[selectedIndex].id = CURRENT_HISTORY_ID;
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

describe("History SelectorModal.vue", () => {
    let wrapper;
    let axiosMock;
    let historyStore;
    const allHistories = getFakeHistorySummaries(15);

    function getUpdatedAxiosMock() {
        const offset = historyStore.historiesOffset;
        axiosMock
            .onGet(`/api/histories?view=summary&order=update_time&offset=${offset}&limit=10`)
            .reply(200, allHistories.slice(offset, offset + 10));

        axiosMock.onGet(`/api/histories/count`).reply(200, 15);
    }

    async function mountWith(props) {
        const pinia = createPinia();
        wrapper = mount(SelectorModal, {
            propsData: props,
            localVue,
            pinia,
        });
        historyStore = useHistoryStore();
        axiosMock = new MockAdapter(axios);
        getUpdatedAxiosMock();
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
        axiosMock.restore();
    });

    it("paginates the histories", async () => {
        await mountWith(PROPS_FOR_MODAL);

        let displayedRows = wrapper.findAllComponents(BListGroupItem).wrappers;
        expect(displayedRows.length).toBe(10);
        expect(wrapper.find(".load-more-hist-button").exists()).toBe(true);

        getUpdatedAxiosMock();
        await historyStore.loadHistories();
        await wrapper.setProps({
            histories: historyStore.histories,
        });

        displayedRows = wrapper.findAllComponents(BListGroupItem).wrappers;
        expect(displayedRows.length).toBe(15);
        expect(wrapper.find(".load-more-hist-button").exists()).toBe(false);
        axiosMock.restore();
    });

    it("emits selectHistory with the correct history ID when a row is clicked", async () => {
        await mountWith(PROPS_FOR_MODAL);

        expect(wrapper.emitted()["selectHistory"]).toBeUndefined();

        const targetHistoryId = "ID-2";
        const targetRow = wrapper.find(`[data-pk="${targetHistoryId}"]`);
        await targetRow.trigger("click");

        expect(wrapper.emitted()["selectHistory"]).toBeDefined();
        expect(wrapper.emitted()["selectHistory"][0][0].id).toBe(targetHistoryId);
        axiosMock.restore();
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

            const button = wrapper.find("footer > .btn-primary");

            await button.trigger("click");

            expect(wrapper.emitted()["selectHistories"][0][0][0].id).toBe(targetHistoryId1);
            axiosMock.restore();
        });
    });
});

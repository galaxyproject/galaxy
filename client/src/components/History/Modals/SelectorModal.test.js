import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { getLocalVue } from "tests/jest/helpers";
import SelectorModal from "./SelectorModal";

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
const PROPS_WITH_10_HISTORIES = {
    currentHistoryId: CURRENT_HISTORY_ID,
    histories: getFakeHistorySummaries(10),
    perPage: 3,
    static: true, // Force the modal visible for testing
};
const PROPS_WITH_10_HISTORY_MULTIPLE_SELECT = {
    ...PROPS_WITH_10_HISTORIES,
    multiple: true,
};

const CURRENT_HISTORY_INDICATION_TEXT = "(Current)";

describe("History SelectorModal.vue", () => {
    let wrapper;

    async function mountWith(props) {
        wrapper = mount(SelectorModal, {
            propsData: props,
            localVue,
        });
        await flushPromises();
    }

    it("should indicate the currently selected history", async () => {
        await mountWith(PROPS_WITH_10_HISTORIES);

        const currentHistoryRow = wrapper.find(`[data-pk="${CURRENT_HISTORY_ID}"]`);
        expect(currentHistoryRow.html()).toContain(CURRENT_HISTORY_INDICATION_TEXT);
    });

    it("paginates the histories", async () => {
        await mountWith(PROPS_WITH_10_HISTORIES);

        const displayedRows = wrapper.findAll("tbody > tr").wrappers;
        expect(displayedRows.length).toBe(3);
        expect(wrapper.vm.histories.length).toBe(10);
    });

    it("emits selectHistory with the correct history ID when a row is clicked", async () => {
        await mountWith(PROPS_WITH_10_HISTORIES);

        expect(wrapper.emitted()["selectHistory"]).toBeUndefined();

        const targetHistoryId = "ID-2";
        const targetRow = wrapper.find(`[data-pk="${targetHistoryId}"]`);
        await targetRow.trigger("click");

        expect(wrapper.emitted()["selectHistory"]).toBeDefined();
        expect(wrapper.emitted()["selectHistory"][0][0].id).toBe(targetHistoryId);
    });

    describe("Multi-selection Mode", () => {
        it("should select multiple histories", async () => {
            await mountWith(PROPS_WITH_10_HISTORY_MULTIPLE_SELECT);

            expect(wrapper.emitted()["selectHistories"]).toBeUndefined();

            const targetHistoryId1 = "ID-1";
            const targetRow1 = wrapper.find(`[data-pk="${targetHistoryId1}"]`);
            await targetRow1.trigger("click");

            const targetHistoryId2 = "ID-2";
            const targetRow2 = wrapper.find(`[data-pk="${targetHistoryId2}"]`);
            await targetRow2.trigger("click");

            expect(wrapper.vm.selectedHistories.length).toBe(2);

            const button = wrapper.find(".btn-primary");

            await button.trigger("click");

            expect(wrapper.emitted()["selectHistories"][0][0][0].id).toBe(targetHistoryId1);

            console.debug(wrapper.html());
        });
    });
});

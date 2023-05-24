import { createPinia } from "pinia";
import { mount } from "@vue/test-utils";
import { useUserStore } from "stores/userStore";
import { useHistoryStore } from "stores/historyStore";
import { getLocalVue } from "tests/jest/helpers";
import flushPromises from "flush-promises";
import HistoryView from "./HistoryView";
import { getHistoryByIdFromServer, setCurrentHistoryOnServer } from "stores/services/history.services";
import MockAdapter from "axios-mock-adapter";
import axios from "axios";

const localVue = getLocalVue();
jest.mock("stores/services/history.services");

function create_history(historyId, userId, purged = false) {
    const historyName = `${userId}'s History ${historyId}`;
    return {
        model_class: "History",
        id: historyId,
        name: historyName,
        purged: purged,
        count: 10,
        annotation: "This is a history",
        tags: ["tag_1", "tag_2"],
        user_id: userId,
        contents_active: {
            deleted: 1,
            hidden: 2,
            active: 8,
        },
    };
}

function create_datasets(historyId, count) {
    const contents = [];
    for (let index = 1; index <= count; index++) {
        contents.push({
            id: `dataset_${index}`,
            name: `Dataset ${index}`,
            history_id: historyId,
            hid: index,
            history_content_type: "dataset",
            deleted: false,
            visible: true,
        });
    }
    return {
        stats: {
            total_matches: count,
        },
        contents: contents,
    };
}

async function createWrapper(localVue, currentUserId, history) {
    const pinia = createPinia();
    getHistoryByIdFromServer.mockResolvedValue(history);
    setCurrentHistoryOnServer.mockResolvedValue(history);
    const axiosMock = new MockAdapter(axios);
    const history_contents_url = `/api/histories/${history.id}/contents?v=dev&order=hid&offset=0&limit=100&q=deleted&qv=false&q=visible&qv=true`;
    const history_contents_result = create_datasets(history.id, history.count);
    axiosMock.onGet(history_contents_url).reply(200, history_contents_result);
    const wrapper = mount(HistoryView, {
        propsData: { id: history.id },
        localVue,
        stubs: {
            icon: { template: "<div></div>" },
        },
        provide: {
            store: {
                dispatch: jest.fn,
                getters: {},
            },
        },
        pinia,
    });
    const userStore = useUserStore();
    const userData = {
        id: currentUserId,
    };
    userStore.currentUser = { ...userStore.currentUser, ...userData };
    await flushPromises();
    return wrapper;
}

describe("History center panel View", () => {
    function expectCorrectLayout(wrapper) {
        // HistoryFilters should exist in HistoryView
        expect(wrapper.find("[data-description='filter text input']").exists()).toBe(true);
        // annotation
        expect(wrapper.find("[data-description='annotation value']").text()).toBe("This is a history");
        // StatelessTags
        const tags = wrapper.find(".stateless-tags");
        expect(tags.text()).toContain("tag_1");
        expect(tags.text()).toContain("tag_2");
        // HistoryCounter
        expect(wrapper.find("[data-description='storage dashboard button']").attributes("disabled")).toBeTruthy();
        expect(wrapper.find("[data-description='show active items button']").text()).toEqual("8");
        expect(wrapper.find("[data-description='include deleted items button']").text()).toEqual("1");
        expect(wrapper.find("[data-description='include hidden items button']").text()).toEqual("2");
    }

    it("current user's current history", async () => {
        const history = create_history("history_1", "user_1", false);
        const wrapper = await createWrapper(localVue, "user_1", history);
        expect(wrapper.vm.history).toEqual(history);

        const historyStore = useHistoryStore();
        await historyStore.setCurrentHistory(history.id);

        // switch/import buttons: current history, should be a disabled switch
        const switchButton = wrapper.find("[data-description='switch to history button']");
        const importButton = wrapper.find("[data-description='import history button']");
        expect(switchButton.attributes("disabled")).toBeTruthy();
        expect(importButton.exists()).toBe(false);

        // parts of the layout that should be similar for all cases
        expectCorrectLayout(wrapper);

        // all history items, make sure all show up with hids and names
        const historyItems = wrapper.findAll(".content-item");
        expect(historyItems.length).toBe(10);
        for (let i = 0; i < historyItems.length; i++) {
            const hid = historyItems.length - i;
            const itemHeader = historyItems.at(i).find("[data-description='content item header info']");
            const headerText = `${hid}: Dataset ${hid}`;
            expect(itemHeader.text()).toBe(headerText);
        }
    });

    it("other user's history", async () => {
        const history = create_history("history_2", "user_2", false);
        const wrapper = await createWrapper(localVue, "user_1", history);
        expect(wrapper.vm.history).toEqual(history);

        // switch/import buttons: external history so should be importable
        const switchButton = wrapper.find("[data-description='switch to history button']");
        const importButton = wrapper.find("[data-description='import history button']");
        expect(switchButton.exists()).toBe(false);
        expect(importButton.attributes("disabled")).toBeFalsy();

        // parts of the layout that should be similar for all cases
        expectCorrectLayout(wrapper);
    });

    it("same user, not current history", async () => {
        const history = create_history("history_3", "user_1", false);
        const wrapper = await createWrapper(localVue, "user_1", history);
        expect(wrapper.vm.history).toEqual(history);

        // switch/import buttons: not current history, switchable
        const switchButton = wrapper.find("[data-description='switch to history button']");
        const importButton = wrapper.find("[data-description='import history button']");
        expect(switchButton.attributes("disabled")).toBeFalsy();
        expect(importButton.exists()).toBe(false);

        // parts of the layout that should be similar for all cases
        expectCorrectLayout(wrapper);
    });

    it("same user, purged history", async () => {
        const history = create_history("history_4", "user_1", true);
        const wrapper = await createWrapper(localVue, "user_1", history);
        expect(wrapper.vm.history).toEqual(history);

        // switch/import buttons: purged they don't exist
        const switchButton = wrapper.find("[data-description='switch to history button']");
        const importButton = wrapper.find("[data-description='import history button']");
        expect(switchButton.exists()).toBe(false);
        expect(importButton.exists()).toBe(false);

        // instead we have an alert
        expect(wrapper.find("[data-description='history state info']").text()).toBe("This history has been purged.");
    });
});

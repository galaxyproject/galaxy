import { getFakeRegisteredUser } from "@tests/test-data";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia } from "pinia";
import { getLocalVue } from "tests/jest/helpers";
import { setupMockConfig } from "tests/jest/mockConfig";

import { useServerMock } from "@/api/client/__mocks__";
import { useHistoryStore } from "@/stores/historyStore";
import { getHistoryByIdFromServer, setCurrentHistoryOnServer } from "@/stores/services/history.services";
import { useUserStore } from "@/stores/userStore";

import ContentItem from "./Content/ContentItem.vue";
import HistoryView from "./HistoryView.vue";

const localVue = getLocalVue();
jest.mock("stores/services/history.services");

const { server, http } = useServerMock();

jest.mock("vue-router/composables", () => ({
    useRoute: jest.fn(() => ({})),
    useRouter: jest.fn(() => ({})),
}));

function create_history(historyId, userId, purged = false, archived = false) {
    const historyName = `${userId}'s History ${historyId}`;
    return {
        model_class: "History",
        id: historyId,
        name: historyName,
        purged: purged,
        archived: archived,
        deleted: purged,
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
    const history_contents_result = create_datasets(history.id, history.count);

    setupMockConfig({});
    server.use(
        http.get("/api/histories/{history_id}/contents", ({ response }) => {
            return response(200).json(history_contents_result);
        })
    );

    const wrapper = mount(HistoryView, {
        propsData: { id: history.id },
        localVue,
        provide: {
            store: {
                dispatch: jest.fn,
                getters: {},
            },
        },
        pinia,
    });
    const userStore = useUserStore();
    userStore.currentUser = getFakeRegisteredUser({ id: currentUserId });
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
        expect(wrapper.find("[data-description='show active items button']").text()).toEqual("8");
        expect(wrapper.find("[data-description='include deleted items button']").text()).toEqual("1");
        expect(wrapper.find("[data-description='include hidden items button']").text()).toEqual("2");
    }

    function storageDashboardButtonDisabled(wrapper) {
        return wrapper.find("[data-description='storage dashboard button']").classes().includes("g-disabled");
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

        // storage dashboard button should be enabled
        expect(storageDashboardButtonDisabled(wrapper)).toBeFalsy();

        // make sure all history items show up
        const historyItems = wrapper.findAllComponents(ContentItem);
        expect(historyItems.length).toBe(10);
        for (let i = 0; i < historyItems.length; i++) {
            const hid = historyItems.length - i;
            expect(historyItems.at(i).props("id")).toBe(hid);
            expect(historyItems.at(i).props("name")).toBe(`Dataset ${hid}`);
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

        // storage dashboard button should be disabled
        expect(storageDashboardButtonDisabled(wrapper)).toBeTruthy();

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

        // storage dashboard button should be enabled
        expect(storageDashboardButtonDisabled(wrapper)).toBeFalsy();

        // parts of the layout that should be similar for all cases
        expectCorrectLayout(wrapper);
    });

    it("same user, purged history", async () => {
        const history = create_history("history_4", "user_1", true);
        const wrapper = await createWrapper(localVue, "user_1", history);
        expect(wrapper.vm.history).toEqual(history);

        // history purged, is switchable but not importable
        const switchButton = wrapper.find("[data-description='switch to history button']");
        const importButton = wrapper.find("[data-description='import history button']");
        expect(switchButton.attributes("disabled")).toBeFalsy();
        expect(importButton.exists()).toBe(false);

        // storage dashboard button can be accessed
        expect(storageDashboardButtonDisabled(wrapper)).toBeFalsy();

        // instead we have an alert
        expect(wrapper.find("[data-description='history messages']").text()).toBe(
            "History has been permanently deleted"
        );
    });

    it("should not display archived message and should be importable when user is not owner and history is archived", async () => {
        const history = create_history("history_2", "user_2", false, true);
        const wrapper = await createWrapper(localVue, "user_1", history);
        expect(wrapper.vm.history).toEqual(history);

        const switchButton = wrapper.find("[data-description='switch to history button']");
        const importButton = wrapper.find("[data-description='import history button']");
        expect(switchButton.exists()).toBe(false);
        expect(importButton.exists()).toBe(true);
        expect(importButton.attributes("disabled")).toBeFalsy();

        // storage dashboard button should be disabled
        expect(storageDashboardButtonDisabled(wrapper)).toBeTruthy();

        expectCorrectLayout(wrapper);
        // There is no message about the history status
        expect(wrapper.find("[data-description='history messages']").text()).toBe("");
    });

    it("should display archived message and should not be importable when user is owner and history is archived", async () => {
        const history = create_history("history_2", "user_1", false, true);
        const wrapper = await createWrapper(localVue, "user_1", history);
        expect(wrapper.vm.history).toEqual(history);

        const switchButton = wrapper.find("[data-description='switch to history button']");
        const importButton = wrapper.find("[data-description='import history button']");
        expect(switchButton.exists()).toBe(true);
        expect(importButton.exists()).toBe(false);

        // storage dashboard button can be accessed
        expect(storageDashboardButtonDisabled(wrapper)).toBeFalsy();

        expectCorrectLayout(wrapper);
        expect(wrapper.find("[data-description='history messages']").text()).toBe("History has been archived");
    });
});

import { getFakeRegisteredUser } from "@tests/test-data";
import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useHistoryStore } from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";

import HistoryOptions from "./HistoryOptions.vue";
import GModal from "@/components/BaseComponents/GModal.vue";

const localVue = getLocalVue();

// all options
const expectedOptions = [
    "Show Histories Side-by-Side",
    "Resume Paused Jobs",
    "Copy History",
    "Copy Datasets",
    "Delete History",
    "Export Tool References",
    "Export History to File",
    "Archive History",
    "Extract Workflow",
    "Show Invocations",
    "Show History Graph",
    "Share & Manage Access",
];

// options enabled for logged-out users
const anonymousOptions = [
    "Resume Paused Jobs",
    "Delete History",
    "Export Tool References",
    "Export History to File",
    "Show History Graph",
];

// options disabled for logged-out users
const anonymousDisabledOptions = expectedOptions.filter((option) => !anonymousOptions.includes(option));

const activeHistory = { id: "history_a", name: "Active History", deleted: false, purged: false, archived: false };
const deletedHistory = { id: "history_b", name: "Deleted History", deleted: true, purged: false, archived: false };

async function createWrapper(propsData: object, userData?: any) {
    const pinia = createPinia();

    const wrapper = shallowMount(HistoryOptions as object, {
        propsData,
        localVue,
        pinia,
    });

    const userStore = useUserStore();
    userStore.currentUser = { ...userStore.currentUser, ...userData };

    const historyStore = useHistoryStore();
    vi.spyOn(historyStore, "currentHistoryId", "get").mockReturnValue("current_history_id");
    vi.spyOn(historyStore, "deleteHistory").mockImplementation(async () => {});

    await flushPromises();
    return { wrapper, historyStore };
}

describe("History Navigation", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it("presents all options to logged-in users", async () => {
        const { wrapper } = await createWrapper(
            {
                history: { id: "current_history_id" },
                histories: [],
            },
            {
                id: "user.id",
                email: "user.email",
            },
        );

        const dropDown = wrapper.find("*[data-description='history options']");
        const optionElements = dropDown.findAll("bdropdownitem-stub");
        const optionTexts = optionElements.wrappers.map((el) => el.text());

        expect(optionTexts).toStrictEqual(expectedOptions);
    });

    it("disables options for anonymous users", async () => {
        const { wrapper } = await createWrapper({
            history: { id: "current_history_id" },
            histories: [],
        });

        const dropDown = wrapper.find("*[data-description='history options']");
        const enabledOptionElements = dropDown.findAll("bdropdownitem-stub:not([disabled])");
        const enabledOptionTexts = enabledOptionElements.wrappers.map((el) => el.text());
        expect(enabledOptionTexts).toStrictEqual(anonymousOptions);

        const disabledOptionElements = dropDown.findAll("bdropdownitem-stub[disabled]");
        const disabledOptionTexts = disabledOptionElements.wrappers.map((el) => el.text());
        expect(disabledOptionTexts).toStrictEqual(anonymousDisabledOptions);
    });

    it("prompts anonymous users to log in", async () => {
        const { wrapper } = await createWrapper({
            history: { id: "current_history_id" },
            histories: [],
        });

        const dropDown = wrapper.find("*[data-description='history options']");
        const disabledOptionElements = dropDown.findAll("bdropdownitem-stub[disabled]");

        disabledOptionElements.wrappers.forEach((option) => {
            expect((option.attributes("title") as string).toLowerCase()).toContain("log in");
        });
    });

    it("shows 'Delete History' for an active history", async () => {
        const { wrapper } = await createWrapper({ history: activeHistory }, getFakeRegisteredUser());
        expect(wrapper.text()).toContain("Delete History");
        expect(wrapper.text()).not.toContain("Permanently Delete History");
    });

    it("shows 'Permanently Delete History' for a deleted (not purged) history", async () => {
        const { wrapper } = await createWrapper({ history: deletedHistory }, getFakeRegisteredUser());
        expect(wrapper.text()).toContain("Permanently Delete History");
    });

    it("delete modal has correct title and ok-text for an active history", async () => {
        const { wrapper } = await createWrapper({ history: activeHistory }, getFakeRegisteredUser());
        const modal = wrapper.findComponent(GModal);
        expect(modal.props("title")).toBe("Delete History?");
        expect(modal.props("okText")).toBe("Delete");
    });

    it("delete modal has correct title and ok-text for a deleted (not purged) history", async () => {
        const { wrapper } = await createWrapper({ history: deletedHistory }, getFakeRegisteredUser());
        const modal = wrapper.findComponent(GModal);
        expect(modal.props("title")).toBe("Permanently Delete History?");
        expect(modal.props("okText")).toBe("Permanently Delete");
    });

    it("purge checkbox is not disabled for an active history", async () => {
        const { wrapper } = await createWrapper({ history: activeHistory }, getFakeRegisteredUser());
        expect(wrapper.find('[data-description="delete history checkbox"]').attributes("disabled")).toBeUndefined();
    });

    it("purge checkbox is disabled for an already-deleted history", async () => {
        const { wrapper } = await createWrapper({ history: deletedHistory }, getFakeRegisteredUser());
        expect(wrapper.find('[data-description="delete history checkbox"]').attributes("disabled")).toBeDefined();
    });

    it("calls deleteHistory with purge=false when checkbox is unchecked", async () => {
        const { wrapper, historyStore } = await createWrapper({ history: activeHistory }, getFakeRegisteredUser());
        wrapper.findComponent(GModal).vm.$emit("ok");
        await flushPromises();
        expect(historyStore.deleteHistory).toHaveBeenCalledWith("history_a", false);
    });

    it("calls deleteHistory with purge=true when purge checkbox is manually checked", async () => {
        const { wrapper, historyStore } = await createWrapper({ history: activeHistory }, getFakeRegisteredUser());
        wrapper.find('[data-description="delete history checkbox"]').vm.$emit("input", true);
        await flushPromises();
        wrapper.findComponent(GModal).vm.$emit("ok");
        await flushPromises();
        expect(historyStore.deleteHistory).toHaveBeenCalledWith("history_a", true);
    });

    it("auto-sets purge=true when history changes to a deleted one while modal is open", async () => {
        // The watch fires on history.id change — covers the case where the modal is already open
        // and the history switches to a deleted one (e.g. another tab deletes it).
        const { wrapper, historyStore } = await createWrapper({ history: activeHistory }, getFakeRegisteredUser());

        expect(wrapper.findComponent(GModal).text()).toContain(activeHistory.name);

        await wrapper.setProps({ history: deletedHistory });

        expect(wrapper.findComponent(GModal).text()).toContain(deletedHistory.name);

        await flushPromises();
        wrapper.findComponent(GModal).vm.$emit("ok");

        await flushPromises();
        expect(historyStore.deleteHistory).toHaveBeenCalledWith("history_b", true);
    });
});

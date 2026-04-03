import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import { createPinia } from "pinia";
import { describe, expect, it, vi } from "vitest";

import { useHistoryStore } from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";

import HistoryOptions from "./HistoryOptions.vue";
import GDropdownItem from "@/components/BaseComponents/GDropdownItem.vue";

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
    "Share & Manage Access",
];

// options enabled for logged-out users
const anonymousOptions = ["Resume Paused Jobs", "Delete History", "Export Tool References", "Export History to File"];

// options disabled for logged-out users
const anonymousDisabledOptions = expectedOptions.filter((option) => !anonymousOptions.includes(option));

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

    return wrapper;
}

describe("History Navigation", () => {
    it("presents all options to logged-in users", async () => {
        const wrapper = await createWrapper(
            {
                history: { id: "current_history_id" },
                histories: [],
            },
            {
                id: "user.id",
                email: "user.email",
            },
        );

        const optionElements = wrapper.findAllComponents(GDropdownItem);
        const optionTexts = optionElements.wrappers.map((el) => el.text());

        expect(optionTexts).toStrictEqual(expectedOptions);
    });

    it("disables options for anonymous users", async () => {
        const wrapper = await createWrapper({
            history: { id: "current_history_id" },
            histories: [],
        });

        const allItems = wrapper.findAllComponents(GDropdownItem);
        const enabledOptionTexts = allItems.wrappers.filter((el) => !el.props("disabled")).map((el) => el.text());
        expect(enabledOptionTexts).toStrictEqual(anonymousOptions);

        const disabledOptionTexts = allItems.wrappers.filter((el) => el.props("disabled")).map((el) => el.text());
        expect(disabledOptionTexts).toStrictEqual(anonymousDisabledOptions);
    });

    it("prompts anonymous users to log in", async () => {
        const wrapper = await createWrapper({
            history: { id: "current_history_id" },
            histories: [],
        });

        const allItems = wrapper.findAllComponents(GDropdownItem);
        const disabledItems = allItems.wrappers.filter((el) => el.props("disabled"));

        disabledItems.forEach((option) => {
            expect((option.props("title") as string).toLowerCase()).toContain("log in");
        });
    });
});

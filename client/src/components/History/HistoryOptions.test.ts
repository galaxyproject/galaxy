import { getLocalVue } from "@tests/jest/helpers";
import { shallowMount } from "@vue/test-utils";
import { createPinia } from "pinia";

import { useHistoryStore } from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";

import HistoryOptions from "./HistoryOptions.vue";

const localVue = getLocalVue();

// all options
const expectedOptions = [
    "Show Histories Side-by-Side",
    "Resume Paused Jobs",
    "Copy this History",
    "Delete this History",
    "Export Tool References",
    "Export History to File",
    "Archive History",
    "Extract Workflow",
    "Show Invocations",
    "Share & Manage Access",
];

// options enabled for logged-out users
const anonymousOptions = [
    "Resume Paused Jobs",
    "Delete this History",
    "Export Tool References",
    "Export History to File",
];

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
    jest.spyOn(historyStore, "currentHistoryId", "get").mockReturnValue("current_history_id");

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
            }
        );

        const dropDown = wrapper.find("*[data-description='history options']");
        const optionElements = dropDown.findAll("bdropdownitem-stub");
        const optionTexts = optionElements.wrappers.map((el) => el.text());

        expect(optionTexts).toStrictEqual(expectedOptions);
    });

    it("disables options for anonymous users", async () => {
        const wrapper = await createWrapper({
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
        const wrapper = await createWrapper({
            history: { id: "current_history_id" },
            histories: [],
        });

        const dropDown = wrapper.find("*[data-description='history options']");
        const disabledOptionElements = dropDown.findAll("bdropdownitem-stub[disabled]");

        disabledOptionElements.wrappers.forEach((option) => {
            expect((option.attributes("title") as string).toLowerCase()).toContain("log in");
        });
    });
});

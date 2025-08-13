import { getLocalVue } from "@tests/jest/helpers";
import { shallowMount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";

import { useUserStore } from "@/stores/userStore";

import HistoryNavigation from "./HistoryNavigation.vue";

const globalConfig = getLocalVue();

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
    setActivePinia(pinia);

    const wrapper = shallowMount(HistoryNavigation as object, {
        props: propsData,
        global: {
            ...globalConfig.global,
            plugins: [...globalConfig.global.plugins, pinia],
        },
    });

    const userStore = useUserStore();
    userStore.currentUser = { ...userStore.currentUser, ...userData };

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

        const createButton = wrapper.find("*[data-description='create new history']");
        expect(createButton.attributes().disabled).toBeFalsy();
        const switchButton = wrapper.find("*[data-description='switch to another history']");
        expect(switchButton.attributes().disabled).toBeFalsy();

        const dropDown = wrapper.find("*[data-description='history options']");
        const optionElements = dropDown.findAll("bdropdownitem-stub");
        const optionTexts = optionElements.map((el) => el.text());

        expect(optionTexts).toStrictEqual(expectedOptions);
    });

    it("disables options for anonymous users", async () => {
        const wrapper = await createWrapper({
            history: { id: "current_history_id" },
            histories: [],
        });

        const createButton = wrapper.find("*[data-description='create new history']");
        expect(createButton.attributes().disabled).toBeTruthy();
        const switchButton = wrapper.find("*[data-description='switch to another history']");
        expect(switchButton.attributes().disabled).toBeTruthy();

        const dropDown = wrapper.find("*[data-description='history options']");
        const enabledOptionElements = dropDown.findAll("bdropdownitem-stub:not([disabled])");
        const enabledOptionTexts = enabledOptionElements.map((el) => el.text());
        expect(enabledOptionTexts).toStrictEqual(anonymousOptions);

        const disabledOptionElements = dropDown.findAll("bdropdownitem-stub[disabled]");
        const disabledOptionTexts = disabledOptionElements.map((el) => el.text());
        expect(disabledOptionTexts).toStrictEqual(anonymousDisabledOptions);
    });

    it("prompts anonymous users to log in", async () => {
        const wrapper = await createWrapper({
            history: { id: "current_history_id" },
            histories: [],
        });

        const dropDown = wrapper.find("*[data-description='history options']");
        const disabledOptionElements = dropDown.findAll("bdropdownitem-stub[disabled]");

        disabledOptionElements.forEach((option) => {
            expect((option.attributes("title") as string).toLowerCase()).toContain("log in");
        });
    });
});

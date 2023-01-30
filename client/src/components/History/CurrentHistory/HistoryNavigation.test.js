import { mockModule, getLocalVue } from "tests/jest/helpers";
import { userStore } from "store/userStore";
import Vuex from "vuex";
import HistoryNavigation from "./HistoryNavigation";
import { shallowMount } from "@vue/test-utils";

const localVue = getLocalVue();

const createStore = (currentUser) => {
    return new Vuex.Store({
        modules: {
            user: mockModule(userStore, { currentUser }),
        },
    });
};

// all options
const expectedOptions = [
    "Show Histories Side-by-Side",
    "Resume Paused Jobs",
    "Copy this History",
    "Delete this History",
    "Export Tool Citations",
    "Export History to File",
    "Extract Workflow",
    "Share or Publish",
    "Set Permissions",
    "Make Private",
];

// options enabled for logged-out users
const anonymousOptions = [
    "Resume Paused Jobs",
    "Delete this History",
    "Export Tool Citations",
    "Export History to File",
];

// options disabled for logged-out users
const anonymousDisabledOptions = expectedOptions.filter((option) => !anonymousOptions.includes(option));

describe("History Navigation", () => {
    it("presents all options to logged-in users", () => {
        const store = createStore({
            id: "user.id",
            email: "user.email",
        });

        const wrapper = shallowMount(HistoryNavigation, {
            propsData: {
                history: { id: "current_history_id" },
                histories: [],
            },
            localVue,
            store,
            provide: { store },
        });

        const createButton = wrapper.find("*[data-description='create new history']");
        expect(createButton.attributes().disabled).toBeFalsy();
        const switchButton = wrapper.find("*[data-description='switch to another history']");
        expect(switchButton.attributes().disabled).toBeFalsy();

        const dropDown = wrapper.find("*[data-description='history options']");
        const optionElements = dropDown.findAll("b-dropdown-item-stub");
        const optionTexts = optionElements.wrappers.map((el) => el.text());

        expect(optionTexts).toStrictEqual(expectedOptions);
    });

    it("disables options for anonymous users", () => {
        const store = createStore({});

        const wrapper = shallowMount(HistoryNavigation, {
            propsData: {
                history: { id: "current_history_id" },
                histories: [],
            },
            localVue,
            store,
            provide: { store },
        });

        const createButton = wrapper.find("*[data-description='create new history']");
        expect(createButton.attributes().disabled).toBeTruthy();
        const switchButton = wrapper.find("*[data-description='switch to another history']");
        expect(switchButton.attributes().disabled).toBeTruthy();

        const dropDown = wrapper.find("*[data-description='history options']");
        const enabledOptionElements = dropDown.findAll("b-dropdown-item-stub:not([disabled])");
        const enabledOptionTexts = enabledOptionElements.wrappers.map((el) => el.text());
        expect(enabledOptionTexts).toStrictEqual(anonymousOptions);

        const disabledOptionElements = dropDown.findAll("b-dropdown-item-stub[disabled]");
        const disabledOptionTexts = disabledOptionElements.wrappers.map((el) => el.text());
        expect(disabledOptionTexts).toStrictEqual(anonymousDisabledOptions);
    });

    it("prompts anonymous users to log in", () => {
        const store = createStore({});

        const wrapper = shallowMount(HistoryNavigation, {
            propsData: {
                history: { id: "current_history_id" },
                histories: [],
            },
            localVue,
            store,
            provide: { store },
        });

        const dropDown = wrapper.find("*[data-description='history options']");
        const disabledOptionElements = dropDown.findAll("b-dropdown-item-stub[disabled]");

        disabledOptionElements.wrappers.forEach((option) => {
            expect(option.attributes("title").toLowerCase()).toContain("log in");
        });
    });
});

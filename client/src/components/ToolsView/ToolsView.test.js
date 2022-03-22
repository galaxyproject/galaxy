import ToolsView from "./ToolsView";
import { mount } from "@vue/test-utils";
import { getLocalVue } from "jest/helpers";
import flushPromises from "flush-promises";

// test response
import testToolsListResponse from "./testData/toolsList";
import testCitation from "./testData/citation";
import MockAdapter from "axios-mock-adapter";
import axios from "axios";

jest.mock("app");

describe("ToolsView/ToolsView.vue", () => {
    const localVue = getLocalVue();

    let wrapper;
    let axiosMock;

    beforeEach(async () => {
        axiosMock = new MockAdapter(axios);
        axiosMock.onGet("/api/tools?tool_help=True").reply(200, testToolsListResponse);
        axiosMock.onGet(new RegExp(`./*/citations`)).reply(200, testCitation);
        wrapper = mount(ToolsView, { localVue, attachTo: document.body });

        await flushPromises();
    });

    afterEach(() => {
        axiosMock.restore();
    });

    it("should render infinite scroll div", async () => {
        expect(wrapper.html()).toEqual(expect.stringContaining('<div infinite-scroll-disabled="busy">'));
    });

    it("should return defined number of tools", async () => {
        expect(wrapper.vm.getToolsNumber() === 5).toBeTruthy();
    });

    it("should render only specific number of tools, equal to current buffer", async () => {
        const buttons = wrapper.findAll('[type="button"]').filter((button) => button.text() === "Info");
        // one 'info' button per tool
        expect(wrapper.vm.buffer.length === buttons.length).toBeTruthy();
    });

    it("should open modal on button click", async () => {
        // findAll() returns WrapperArray, thus regular array.find() won't work
        const infoButton = wrapper
            .findAll('[type="button"]')
            .filter((button) => button.text() === "Info")
            .at(0);
        const modalId = "modal--" + infoButton.attributes().index;
        const modal = wrapper.find("#" + modalId);
        expect(modal.element).not.toBeVisible();
        await infoButton.trigger("click");
        await flushPromises();

        expect(modal.element).toBeVisible();
    });

    it("citation should open on click", async () => {
        const infoButton = wrapper
            .findAll('[type="button"]')
            .filter((button) => button.text() === "Citations")
            .at(0);
        const citation = wrapper.find("#" + infoButton.attributes("aria-controls").replace(/ /g, "_"));

        expect(citation.element).not.toBeVisible();
        expect(infoButton.attributes("aria-expanded") === "false").toBeTruthy();

        await infoButton.trigger("click");
        await flushPromises();
        expect(infoButton.attributes("aria-expanded") === "true").toBeTruthy();
        expect(citation.element).toBeVisible();
    });
});

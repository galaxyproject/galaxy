/* global expect */
import ToolsView from "./ToolsView";
import { shallowMount, mount, createLocalVue } from "@vue/test-utils";
import _l from "utils/localization";
import Vue from "vue";

// test response
import testToolsListResponse from "./testData/toolsList";
import MockAdapter from "axios-mock-adapter";
import axios from "axios";

describe("ToolsView/ToolsView.vue", () => {
    const localVue = createLocalVue();
    localVue.filter("localize", value => _l(value));
    let wrapper, emitted, axiosMock;

    beforeEach(async () => {
        axiosMock = new MockAdapter(axios);
        // using shallow because of inner 'Citation' component
        wrapper = mount(ToolsView);
        emitted = wrapper.emitted();
        axiosMock.onGet("/api/tools?tool_help=True").reply(200, testToolsListResponse);
        await Vue.nextTick();
        await Vue.nextTick();
    });

    afterEach(() => {
        axiosMock.restore();
    });

    it("should render infinite scroll div", async () => {
        expect(wrapper.html()).contain('<div infinite-scroll-disabled="busy">');
    });

    it("should return defined number of tools", async () => {
        assert(wrapper.vm.getToolsNumber() === 84, "Tools Get Response is not parsed correctly!");
    });

    it("should render only specific number of tools, equal to current buffer", async () => {
        let buttons = wrapper.findAll('[type="button"]').filter(button => button.text() === "Info");
        // one 'info' button per tool
        assert(wrapper.vm.buffer.length === buttons.length, "Number of 'info' buttons do not equal the buffer size!");
    });
    it("should open modal on button click", async () => {
        // findAll() returns WrapperArray, thus regular array.find() won't work
        let infoButton = wrapper
            .findAll('[type="button"]')
            .filter(button => button.text() === "Info")
            .at(0);
        const modalId = "modal--" + infoButton.attributes().index;
        const modal = wrapper.find("#" + modalId);
        assert(modal.isVisible() === false, "modal is visible before the click!");

        infoButton.trigger("click");
        await Vue.nextTick();

        assert(modal.isVisible(), "'Info' button didn't open a modal!");
    });
});

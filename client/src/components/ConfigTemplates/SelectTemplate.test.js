import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";

import { STANDARD_FILE_SOURCE_TEMPLATE } from "./test_fixtures";

import SelectTemplate from "./SelectTemplate.vue";

const localVue = getLocalVue(true);

const help = "some help text about selection";

describe("SelectTemplate", () => {
    it("should render a selection row for supplied templates", async () => {
        const wrapper = mount(SelectTemplate, {
            propsData: {
                templates: [STANDARD_FILE_SOURCE_TEMPLATE],
                selectText: help,
                idPrefix: "file-source",
            },
            localVue,
        });
        const helpText = wrapper.find(".file-source-template-select-help");
        expect(helpText.exists()).toBeTruthy();
        expect(helpText.text()).toBeLocalizationOf(help);
        const buttons = wrapper.findAll("button");
        expect(buttons.length).toBe(1);
        const button = buttons.at(0);
        expect(button.attributes().id).toEqual("file-source-template-button-moo");
        expect(button.attributes()["data-template-id"]).toEqual("moo");
        expect(button.text()).toEqual("moo");
    });
});

import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import { sanitizeHtml } from "@/directives/sanitizeHtml";

import ToolHelpRst from "./ToolHelpRst.vue";

const localVue = getLocalVue();

const inputHelpText = `
<h1>Tool Help</h1>
<p>Hello World</p>
<h2><b>Heading h2</b></h2>
<span>Text</span>
<h2 class="red">Heading</h2>
<h3>h3 Heading</h3>
<h4>h4 Heading</h4>
<a>empty link</a>`;

const expectedHelpText = `
<h3>Tool Help</h3>
<p>Hello World</p>
<h4><b>Heading h2</b></h4>
<span>Text</span>
<h4 class="red">Heading</h4>
<h5>h3 Heading</h5>
<h6>h4 Heading</h6>
<a target="_blank">empty link</a>`;

describe("ToolHelp RST", () => {
    it("modifies help text", () => {
        const wrapper = mount(ToolHelpRst, {
            propsData: {
                content: inputHelpText,
            },
            localVue,
        });

        const help = wrapper.find(".form-help");
        expect(help.element).toContainHTML(expectedHelpText.trim());
    });

    it("renders the formatted help through v-sanitize-html with the links profile", () => {
        vi.mocked(sanitizeHtml).mockClear();
        mount(ToolHelpRst, { propsData: { content: '<a href="https://galaxyproject.org">link</a>' }, localVue });
        expect(sanitizeHtml).toHaveBeenCalledWith(
            '<a href="https://galaxyproject.org" target="_blank">link</a>',
            "links",
        );
    });
});

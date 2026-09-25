import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, test, vi } from "vitest";
import { defineComponent, nextTick } from "vue";

import { sanitizeHtml } from "@/directives/sanitizeHtml";

// The directive is registered globally by the test setup, with sanitizeHtml
// replaced by a pass-through spy; here it is swapped for a marker so the tests
// can tell sanitized output apart from the raw input.
const sanitizeSpy = vi.mocked(sanitizeHtml);

function mountWith(value: unknown, directive = "v-sanitize-html") {
    const Host = defineComponent({
        props: {
            value: { type: null, default: null },
            other: { type: Number, default: 0 },
        },
        template: `<div><span data-other>{{ other }}</span><div class="target" ${directive}="value" /></div>`,
    });
    return mount(Host as object, { propsData: { value } });
}

describe("v-sanitize-html", () => {
    beforeEach(() => {
        sanitizeSpy.mockReset();
        sanitizeSpy.mockImplementation((html) => `<i>sanitized:${html}</i>`);
    });

    test("renders the sanitizer output for a string with the default profile", () => {
        const wrapper = mountWith("<b>hello</b>");
        expect(sanitizeSpy).toHaveBeenCalledWith("<b>hello</b>", "default");
        expect(wrapper.find(".target").element.innerHTML).toBe("<i>sanitized:<b>hello</b></i>");
    });

    test("uses the directive argument as the profile", () => {
        const wrapper = mountWith("<a>x</a>", "v-sanitize-html:links");
        expect(sanitizeSpy).toHaveBeenCalledWith("<a>x</a>", "links");
        expect(wrapper.find(".target").element.innerHTML).toBe("<i>sanitized:<a>x</a></i>");
    });

    test("treats null and undefined as empty", () => {
        mountWith(null);
        mountWith(undefined);
        expect(sanitizeSpy.mock.calls).toEqual([
            ["", "default"],
            ["", "default"],
        ]);
    });

    test("renders nothing and warns for values that aren't strings", () => {
        const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
        for (const value of [{ nested: "message" }, ["a", "b"], 42]) {
            const wrapper = mountWith(value);
            expect(wrapper.find(".target").element.innerHTML).toBe("<i>sanitized:</i>");
        }
        expect(sanitizeSpy.mock.calls.every(([html]) => html === "")).toBe(true);
        expect(warn).toHaveBeenCalledTimes(3);
        warn.mockRestore();
    });

    test("re-sanitizes when the bound value changes", async () => {
        const wrapper = mountWith("first", "v-sanitize-html:links");
        await wrapper.setProps({ value: "second" });
        expect(sanitizeSpy).toHaveBeenLastCalledWith("second", "links");
        expect(wrapper.find(".target").element.innerHTML).toBe("<i>sanitized:second</i>");
    });

    test("leaves the DOM alone when an unrelated re-render keeps the same content", async () => {
        const wrapper = mountWith("same", "v-sanitize-html:links");
        const target = wrapper.find(".target").element;
        target.querySelector("i")!.setAttribute("data-decorated", "yes");
        sanitizeSpy.mockClear();

        await wrapper.setProps({ other: 1 });
        await nextTick();

        expect(wrapper.find("[data-other]").text()).toBe("1");
        expect(sanitizeSpy).not.toHaveBeenCalled();
        expect(target.querySelector("i")!.getAttribute("data-decorated")).toBe("yes");
    });
});

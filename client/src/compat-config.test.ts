import { faCopy } from "@fortawesome/free-regular-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import { h, nextTick, ref } from "vue";

describe("FontAwesomeIcon under the compat config", () => {
    it("binds listeners to the svg", async () => {
        const onClick = vi.fn();
        const wrapper = mount({ render: () => h(FontAwesomeIcon, { icon: faCopy, onClick }) });
        await wrapper.find("svg").trigger("click");
        expect(onClick).toHaveBeenCalledTimes(1);
    });

    it("passes class, style and attributes to the svg", () => {
        const wrapper = mount({
            render: () =>
                h(FontAwesomeIcon, {
                    icon: faCopy,
                    class: "copy-icon",
                    style: { cursor: "pointer" },
                    "data-description": "copy",
                }),
        });
        const svg = wrapper.find("svg");
        expect(svg.classes()).toContain("copy-icon");
        expect(svg.classes()).toContain("svg-inline--fa");
        expect(svg.attributes("style")).toContain("cursor: pointer");
        expect(svg.attributes("data-description")).toBe("copy");
    });

    it("updates attributes that change after the first render", async () => {
        const label = ref("first");
        const wrapper = mount({ render: () => h(FontAwesomeIcon, { icon: faCopy, "data-label": label.value }) });
        label.value = "second";
        await nextTick();
        expect(wrapper.find("svg").attributes("data-label")).toBe("second");
    });
});

import { faInfoCircle } from "@fortawesome/free-solid-svg-icons";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import DetailBlock from "./DetailBlock.vue";

const localVue = getLocalVue();

function mountDetailBlock(props: Record<string, unknown> = {}) {
    return mount(DetailBlock as object, {
        props: { headerIcon: faInfoCircle, title: "Details", collapsible: true, ...props },
        slots: { default: "<p>content</p>" },
        global: localVue,
    });
}

function isContentVisible(wrapper: ReturnType<typeof mountDetailBlock>) {
    return wrapper.findComponent({ name: "GCollapse" }).props("visible");
}

async function toggle(wrapper: ReturnType<typeof mountDetailBlock>) {
    wrapper.findComponent({ name: "GHeading" }).vm.$emit("click");
    await wrapper.vm.$nextTick();
}

describe("DetailBlock", () => {
    it("toggles its own collapse state when `collapsed` is omitted", async () => {
        const wrapper = mountDetailBlock();
        expect(isContentVisible(wrapper)).toBe(true);

        await toggle(wrapper);

        expect(isContentVisible(wrapper)).toBe(false);
        expect(wrapper.emitted("update:collapsed")).toBeUndefined();
    });

    it("only emits `update:collapsed` when `collapsed` is controlled by the parent", async () => {
        const wrapper = mountDetailBlock({ collapsed: false });

        await toggle(wrapper);

        expect(wrapper.emitted("update:collapsed")).toEqual([[true]]);
        expect(isContentVisible(wrapper)).toBe(true);
    });
});

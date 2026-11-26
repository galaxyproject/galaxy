import { enableAutoUnmount, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";
import { defineComponent } from "vue";

import GLink from "./GLink.vue";

enableAutoUnmount(afterEach);

function mountInForm(linkAttrs: Record<string, unknown> = {}) {
    const onSubmit = vi.fn();
    const FormWithLink = defineComponent({
        components: { GLink },
        setup: () => ({ linkAttrs, onSubmit }),
        template: `<form @submit.prevent="onSubmit"><GLink v-bind="linkAttrs">Link</GLink></form>`,
    });
    const wrapper = mount(FormWithLink, { attachTo: document.body });
    return { wrapper, onSubmit };
}

describe("GLink", () => {
    it("does not submit the surrounding form when rendered as a button", async () => {
        const { wrapper, onSubmit } = mountInForm();

        const link = wrapper.get(".g-link");
        expect(link.element.tagName).toBe("BUTTON");
        expect(link.attributes("type")).toBe("button");

        await link.trigger("click");
        expect(onSubmit).not.toHaveBeenCalled();
    });

    it("keeps a type the caller sets", async () => {
        const { wrapper, onSubmit } = mountInForm({ type: "submit" });

        const link = wrapper.get(".g-link");
        expect(link.attributes("type")).toBe("submit");

        await link.trigger("click");
        expect(onSubmit).toHaveBeenCalledTimes(1);
    });

    it("sets no type on an anchor", () => {
        const { wrapper } = mountInForm({ href: "#target" });

        const link = wrapper.get(".g-link");
        expect(link.element.tagName).toBe("A");
        expect(link.attributes("type")).toBeUndefined();
    });
});

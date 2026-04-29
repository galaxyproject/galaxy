import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import FormMessage from "./FormMessage.vue";

vi.mock("app");

const localVue = getLocalVue();

describe("FormMessage", () => {
    let wrapper;

    beforeEach(() => {
        vi.useFakeTimers();
        wrapper = mount(FormMessage, {
            props: {
                message: "test message",
                variant: "danger",
                persistent: true,
                timeout: 1000,
            },
            global: localVue,
        });
    });

    it("check persistent message and status", async () => {
        const variants = wrapper.findAll(".alert-danger");
        expect(variants.length).toBe(1);
        const message = wrapper.find(".alert");
        expect(message.text()).toBe("test message");
    });

    it("check transient message and status", async () => {
        await wrapper.setProps({
            persistent: false,
            variant: "info",
            message: "new message",
        });
        const variants = wrapper.findAll(".alert-info");
        expect(variants.length).toBe(1);
        const message = wrapper.find(".alert");
        expect(message.text()).toBe("new message");
        vi.advanceTimersByTime(1000);
        await wrapper.vm.$nextTick();
        const new_variants = wrapper.findAll(".alert-info");
        expect(new_variants.length).toBe(0);
        await wrapper.setProps({
            variant: "warning",
            message: "last message",
        });
        const last_message = wrapper.find(".alert");
        expect(last_message.text()).toBe("last message");
    });
});

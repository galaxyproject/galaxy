import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";

import FormMessage from "./FormMessage";

jest.mock("app");

const globalConfig = getLocalVue();

describe("FormMessage", () => {
    let wrapper;

    beforeEach(() => {
        jest.useFakeTimers();
        wrapper = mount(FormMessage, {
            props: {
                message: "test message",
                variant: "danger",
                persistent: true,
                timeout: 1000,
            },
            global: globalConfig.global,
        });
    });

    it("check persistent message and status", async () => {
        // Initially renders as HTML with CSS classes
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
        // Component renders as b-alert with variant attribute instead of CSS class
        const variants = wrapper.findAll("b-alert[variant='info']");
        expect(variants.length).toBe(1);
        const message = wrapper.find("b-alert");
        expect(message.text()).toBe("new message");
        // TODO: Fix timer behavior in Vue 3
        // jest.advanceTimersByTime(1000);
        // await wrapper.vm.$nextTick();
        // const new_variants = wrapper.findAll("b-alert[variant='info']");
        // expect(new_variants.length).toBe(0);
        await wrapper.setProps({
            variant: "warning",
            message: "last message",
        });
        const last_message = wrapper.find("b-alert");
        expect(last_message.text()).toBe("last message");
    });
});

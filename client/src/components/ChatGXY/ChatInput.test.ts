import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import ChatInput from "./ChatInput.vue";

function mountInput(props: Record<string, unknown> = {}) {
    return mount(ChatInput as any, {
        propsData: {
            value: "",
            busy: false,
            ...props,
        },
        stubs: {
            FontAwesomeIcon: true,
            LoadingSpan: true,
        },
    });
}

describe("ChatInput", () => {
    describe("rendering", () => {
        it("renders textarea with provided value", () => {
            const wrapper = mountInput({ value: "hello" });
            const textarea = wrapper.find("textarea");
            expect((textarea.element as HTMLTextAreaElement).value).toBe("hello");
        });

        it("renders with default placeholder", () => {
            const wrapper = mountInput();
            const textarea = wrapper.find("textarea");
            expect(textarea.attributes("placeholder")).toContain("Ask about tools");
        });

        it("renders with custom placeholder", () => {
            const wrapper = mountInput({ placeholder: "Type here..." });
            expect(wrapper.find("textarea").attributes("placeholder")).toBe("Type here...");
        });

        it("has accessible label", () => {
            const wrapper = mountInput();
            expect(wrapper.find("label[for='chat-input']").exists()).toBe(true);
        });
    });

    describe("disabled states", () => {
        it("disables textarea when busy", () => {
            const wrapper = mountInput({ busy: true });
            expect((wrapper.find("textarea").element as HTMLTextAreaElement).disabled).toBe(true);
        });

        it("disables textarea when disabled prop is true", () => {
            const wrapper = mountInput({ disabled: true });
            expect((wrapper.find("textarea").element as HTMLTextAreaElement).disabled).toBe(true);
        });

        it("disables send button when value is empty", () => {
            const wrapper = mountInput({ value: "" });
            expect((wrapper.find("button").element as HTMLButtonElement).disabled).toBe(true);
        });

        it("disables send button when value is whitespace", () => {
            const wrapper = mountInput({ value: "   " });
            expect((wrapper.find("button").element as HTMLButtonElement).disabled).toBe(true);
        });

        it("enables send button when value has content", () => {
            const wrapper = mountInput({ value: "hello" });
            expect((wrapper.find("button").element as HTMLButtonElement).disabled).toBe(false);
        });

        it("disables send button when busy even with content", () => {
            const wrapper = mountInput({ value: "hello", busy: true });
            expect((wrapper.find("button").element as HTMLButtonElement).disabled).toBe(true);
        });
    });

    describe("events", () => {
        it("emits input on textarea input", async () => {
            const wrapper = mountInput();
            const textarea = wrapper.find("textarea");
            await textarea.setValue("hello");
            expect(wrapper.emitted("input")).toBeTruthy();
            const emitted = wrapper.emitted("input")!;
            expect(emitted[emitted.length - 1]![0]).toBe("hello");
        });

        it("emits submit on send button click", async () => {
            const wrapper = mountInput({ value: "hello" });
            await wrapper.find("button").trigger("click");
            expect(wrapper.emitted("submit")).toBeTruthy();
        });

        it("emits submit on Enter key (without Shift)", async () => {
            const wrapper = mountInput({ value: "hello" });
            await wrapper.find("textarea").trigger("keydown.enter");
            expect(wrapper.emitted("submit")).toBeTruthy();
        });

        it("does not emit submit on Shift+Enter", async () => {
            const wrapper = mountInput({ value: "hello" });
            await wrapper.find("textarea").trigger("keydown.enter", { shiftKey: true });
            expect(wrapper.emitted("submit")).toBeFalsy();
        });
    });

    describe("busy state UI", () => {
        it("shows loading indicator when busy", () => {
            const wrapper = mountInput({ busy: true });
            expect(wrapper.findComponent({ name: "LoadingSpan" }).exists()).toBe(true);
        });

        it("hides loading indicator when not busy", () => {
            const wrapper = mountInput({ busy: false });
            expect(wrapper.findComponent({ name: "LoadingSpan" }).exists()).toBe(false);
        });
    });
});

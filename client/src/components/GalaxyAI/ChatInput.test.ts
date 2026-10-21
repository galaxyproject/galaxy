import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { emittedArg } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, describe, expect, it, onTestFinished, vi } from "vitest";

import GButton from "../BaseComponents/GButton.vue";
import ChatInput from "./ChatInput.vue";

vi.mock("@/stores/historyStore", () => ({
    useHistoryStore: () => ({ currentHistoryId: null, currentHistory: null }),
}));
vi.mock("@/stores/historyItemsStore", () => ({
    useHistoryItemsStore: () => ({ getHistoryItems: () => [] }),
}));

function mountInput(
    props: Partial<InstanceType<typeof ChatInput>["$props"]> = {},
    stubs: Record<string, boolean> = {
        LoadingSpan: true,
        MentionDropdown: true,
    },
) {
    return mount(ChatInput, {
        props: {
            value: "",
            busy: false,
            ...props,
        },
        global: { stubs },
    });
}

enableAutoUnmount(afterEach);
afterEach(async () => {
    // Let the real mention dropdown finish positioning before its owned wrapper is unmounted.
    await flushPromises();
});

describe("ChatInput", () => {
    describe("rendering", () => {
        it("renders textarea with provided value", () => {
            const wrapper = mountInput({ value: "hello" });
            const textarea = wrapper.get<HTMLTextAreaElement>("textarea");
            expect(textarea.element.value).toBe("hello");
        });

        it("renders with default placeholder", () => {
            const wrapper = mountInput();
            const textarea = wrapper.get<HTMLTextAreaElement>("textarea");
            expect(textarea.attributes("placeholder")).toContain("Ask about tools");
        });

        it("renders with custom placeholder", () => {
            const wrapper = mountInput({ placeholder: "Type here..." });
            expect(wrapper.get<HTMLTextAreaElement>("textarea").attributes("placeholder")).toBe("Type here...");
        });

        it("has accessible label", () => {
            const wrapper = mountInput();
            expect(wrapper.find("label[for='chat-input']").exists()).toBe(true);
        });
    });

    describe("disabled states", () => {
        it("disables textarea when busy", () => {
            const wrapper = mountInput({ busy: true });
            expect(wrapper.get<HTMLTextAreaElement>("textarea").element.disabled).toBe(true);
        });

        it("disables textarea when disabled prop is true", () => {
            const wrapper = mountInput({ disabled: true });
            expect(wrapper.get<HTMLTextAreaElement>("textarea").element.disabled).toBe(true);
        });

        it("disables send button when value is empty", () => {
            const wrapper = mountInput({ value: "" });
            expect(wrapper.getComponent(GButton).props("disabled")).toBe(true);
        });

        it("disables send button when value is whitespace", () => {
            const wrapper = mountInput({ value: "   " });
            expect(wrapper.getComponent(GButton).props("disabled")).toBe(true);
        });

        it("enables send button when value has content", () => {
            const wrapper = mountInput({ value: "hello" });
            expect(wrapper.getComponent(GButton).props("disabled")).toBe(false);
        });

        it("disables send button when busy even with content", () => {
            const wrapper = mountInput({ value: "hello", busy: true });
            expect(wrapper.getComponent(GButton).props("disabled")).toBe(true);
        });

        it("disables send button when disabled prop is true even with content", () => {
            const wrapper = mountInput({ value: "hello", disabled: true });
            expect(wrapper.getComponent(GButton).props("disabled")).toBe(true);
        });
    });

    describe("events", () => {
        it("emits input on textarea input", async () => {
            const wrapper = mountInput();
            const textarea = wrapper.get<HTMLTextAreaElement>("textarea");
            await textarea.setValue("hello");
            expect(wrapper.emitted("input")).toBeTruthy();
            expect(emittedArg(wrapper, "input", -1)).toBe("hello");
        });

        it("emits submit on send button click", async () => {
            const wrapper = mountInput({ value: "hello" });
            await wrapper.getComponent(GButton).trigger("click");
            expect(wrapper.emitted("submit")).toBeTruthy();
        });

        it("emits submit on Enter key (without Shift)", async () => {
            const wrapper = mountInput({ value: "hello" });
            await wrapper.get<HTMLTextAreaElement>("textarea").trigger("keydown", { key: "Enter" });
            expect(wrapper.emitted("submit")).toBeTruthy();
        });

        it("does not emit submit on Shift+Enter", async () => {
            const wrapper = mountInput({ value: "hello" });
            await wrapper.get<HTMLTextAreaElement>("textarea").trigger("keydown", { key: "Enter", shiftKey: true });
            expect(wrapper.emitted("submit")).toBeFalsy();
        });

        it("emits submit on Enter when the mention dropdown has no matches", async () => {
            const value = "@dataset:nope";
            const wrapper = mountInput({ value }, { FontAwesomeIcon: true, LoadingSpan: true });
            const textarea = wrapper.get<HTMLTextAreaElement>("textarea");
            const el = textarea.element;
            el.selectionStart = value.length;
            el.selectionEnd = value.length;

            await textarea.trigger("input");
            await textarea.trigger("keydown", { key: "Enter" });

            expect(wrapper.emitted("submit")).toBeTruthy();
        });

        it("closes an empty mention dropdown on Escape", async () => {
            const value = "@dataset:nope";
            const wrapper = mountInput({ value }, { FontAwesomeIcon: true, LoadingSpan: true });
            const textarea = wrapper.get<HTMLTextAreaElement>("textarea");
            const el = textarea.element;
            el.selectionStart = value.length;
            el.selectionEnd = value.length;

            await textarea.trigger("input");
            expect(wrapper.get(".mention-dropdown").attributes("style") ?? "").not.toContain("display: none");

            await textarea.trigger("keydown", { key: "Escape" });

            expect(wrapper.get(".mention-dropdown").attributes("style") ?? "").toContain("display: none");
        });
    });

    describe("auto-resize", () => {
        function mockScrollHeight(el: HTMLTextAreaElement, value: number) {
            Object.defineProperty(el, "scrollHeight", { configurable: true, value });
        }

        it("does not set height on mount when value is empty", () => {
            const wrapper = mountInput({ value: "" });
            const el = wrapper.get<HTMLTextAreaElement>("textarea").element;
            expect(el.style.height).toBe("");
        });

        it("sizes the textarea to its content on mount when value is non-empty", () => {
            // onMounted resizes synchronously, so mock scrollHeight on the
            // prototype before mounting and restore it afterwards.
            const proto = window.HTMLTextAreaElement.prototype;
            const original = Object.getOwnPropertyDescriptor(proto, "scrollHeight");
            onTestFinished(() => {
                if (original) {
                    Object.defineProperty(proto, "scrollHeight", original);
                } else {
                    Reflect.deleteProperty(proto, "scrollHeight");
                }
            });
            Object.defineProperty(proto, "scrollHeight", { configurable: true, get: () => 96 });
            const wrapper = mountInput({ value: "line one\nline two\nline three" });
            const el = wrapper.get<HTMLTextAreaElement>("textarea").element;
            expect(el.style.height).toBe("96px");
        });

        it("grows when the value changes (typing / mention insert)", async () => {
            const wrapper = mountInput({ value: "short" });
            const el = wrapper.get<HTMLTextAreaElement>("textarea").element;

            mockScrollHeight(el, 120);
            await wrapper.setProps({ value: "much\nlonger\ncontent\nhere" });
            await wrapper.vm.$nextTick();

            expect(el.style.height).toBe("120px");
        });

        it("resets height to '' when value is cleared (e.g. after submit)", async () => {
            const wrapper = mountInput({ value: "a\nb\nc\nd\ne" });
            const el = wrapper.get<HTMLTextAreaElement>("textarea").element;

            mockScrollHeight(el, 140);
            await wrapper.setProps({ value: "a\nb\nc\nd\ne\nf" });
            await wrapper.vm.$nextTick();
            expect(el.style.height).toBe("140px");

            await wrapper.setProps({ value: "" });
            await wrapper.vm.$nextTick();
            expect(el.style.height).toBe("");
        });
    });

    describe("busy state UI", () => {
        it("shows spinner icon when busy", () => {
            const wrapper = mountInput({ busy: true });
            const buttonIcon = wrapper.getComponent(GButton).getComponent(FontAwesomeIcon);
            expect(buttonIcon.classes()).toContain("fa-spinner");
            expect(buttonIcon.classes()).toContain("fa-spin");
            expect(buttonIcon.classes()).not.toContain("fa-paper-plane");
        });

        it("shows send icon when not busy", () => {
            const wrapper = mountInput({ busy: false });
            const buttonIcon = wrapper.getComponent(GButton).getComponent(FontAwesomeIcon);
            expect(buttonIcon.classes()).toContain("fa-paper-plane");
            expect(buttonIcon.classes()).not.toContain("fa-spinner");
            expect(buttonIcon.classes()).not.toContain("fa-spin");
        });
    });
});

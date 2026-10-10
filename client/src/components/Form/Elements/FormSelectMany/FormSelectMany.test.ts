import "./worker/__mocks__/selectMany";

import { createTestingPinia } from "@pinia/testing";
import { emittedArg, getLocalVue, nth, withPlugins } from "@tests/vitest/helpers";
import { enableAutoUnmount, shallowMount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { SelectOption, SelectValue } from "./worker/selectMany";

import FormSelectMany from "./FormSelectMany.vue";

enableAutoUnmount(afterEach);

beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());

function mountSelectMany(props: Partial<InstanceType<typeof FormSelectMany>["$props"]>) {
    const global = withPlugins(getLocalVue(), createTestingPinia({ createSpy: vi.fn }));
    return shallowMount(FormSelectMany, {
        props: { options: [], value: [], ...props },
        global: { ...global, stubs: { ...global.stubs, BFormInput: false, GButton: false } },
    });
}

const selectors = {
    unselectedOptions: ".options-list.unselected > button",
    unselectedHighlighted: ".options-list.unselected > button.highlighted",
    selectedOptions: ".options-list:not(.unselected) > button",
    selectedHighlighted: ".options-list:not(.unselected) > button.highlighted",
    selectAll: ".selection-button.select",
    deselectAll: ".selection-button.deselect",
    selectedCount: ".selected-count",
    unselectedCount: ".unselected-count",
    search: "input[type=search]",
    caseSensitivity: ".toggle-button.case-sensitivity",
    useRegex: ".toggle-button.use-regex",
} as const;

function emailOptions(prefixes = ["foo", "bar", "baz"]): SelectOption[] {
    return prefixes.flatMap((prefix) =>
        [".com", ".org"].map((suffix) => {
            const email = `${prefix}@galaxy${suffix}`;
            return { label: email, value: email };
        }),
    );
}

// Model the parent applying the latest selection emitted by this controlled input.
async function applyInput(wrapper: ReturnType<typeof mountSelectMany>) {
    const value = emittedArg(wrapper, "input", -1) as SelectValue[];
    await wrapper.setProps({ value });
    return value;
}

async function search(wrapper: ReturnType<typeof mountSelectMany>, value: string) {
    await wrapper.find(selectors.search).setValue(value);
    await vi.runAllTimersAsync();
}

function labels(wrapper: ReturnType<typeof mountSelectMany>, selector: string) {
    return wrapper.findAll(selector).map((option) => option.text());
}

describe("FormSelectMany", () => {
    it("displays all six options in their supplied order", () => {
        const options = emailOptions();
        const wrapper = mountSelectMany({ options });

        expect(wrapper.findAll(selectors.unselectedOptions)).toHaveLength(6);
        expect(labels(wrapper, selectors.unselectedOptions)).toEqual(options.map((option) => option.label));
    });

    it("appends clicked options to the emitted selection", async () => {
        const wrapper = mountSelectMany({ options: emailOptions() });

        await nth(wrapper.findAll(selectors.unselectedOptions), 0).trigger("click");
        expect(await applyInput(wrapper)).toEqual(["foo@galaxy.com"]);

        await nth(wrapper.findAll(selectors.unselectedOptions), 0).trigger("click");
        expect(await applyInput(wrapper)).toEqual(["foo@galaxy.com", "foo@galaxy.org"]);
    });

    it("moves selected values between columns when the parent applies an input event", async () => {
        const wrapper = mountSelectMany({ options: emailOptions(), value: ["foo@galaxy.com", "foo@galaxy.org"] });

        expect(labels(wrapper, selectors.selectedOptions)).toEqual(["foo@galaxy.com", "foo@galaxy.org"]);
        for (const option of labels(wrapper, selectors.unselectedOptions)) {
            expect(option).not.toBe("foo@galaxy.com");
            expect(option).not.toBe("foo@galaxy.org");
        }

        await nth(wrapper.findAll(selectors.unselectedOptions), 0).trigger("click");
        const emitted = await applyInput(wrapper);

        expect(wrapper.findAll(selectors.selectedOptions)).toHaveLength(3);
        expect(nth(wrapper.findAll(selectors.selectedOptions), 2).text()).toBe(nth(emitted, 2));
        for (const option of labels(wrapper, selectors.unselectedOptions)) {
            expect(option).not.toBe(nth(emitted, 2));
        }
    });

    it("updates both column counts after selecting another option", async () => {
        const wrapper = mountSelectMany({ options: emailOptions(), value: ["foo@galaxy.com", "foo@galaxy.org"] });

        expect(wrapper.find(selectors.selectedCount).text()).toBe("(2)");
        expect(wrapper.find(selectors.unselectedCount).text()).toBe("(4)");

        await nth(wrapper.findAll(selectors.unselectedOptions), 0).trigger("click");
        await applyInput(wrapper);

        expect(wrapper.find(selectors.selectedCount).text()).toBe("(3)");
        expect(wrapper.find(selectors.unselectedCount).text()).toBe("(3)");
    });

    it("selects all remaining options and then deselects all six", async () => {
        const wrapper = mountSelectMany({ options: emailOptions(), value: ["foo@galaxy.com", "foo@galaxy.org"] });

        await wrapper.find(selectors.selectAll).trigger("click");
        await applyInput(wrapper);
        expect(wrapper.findAll(selectors.unselectedOptions)).toHaveLength(0);
        expect(wrapper.findAll(selectors.selectedOptions)).toHaveLength(6);

        await wrapper.find(selectors.deselectAll).trigger("click");
        await applyInput(wrapper);
        expect(wrapper.findAll(selectors.unselectedOptions)).toHaveLength(6);
        expect(wrapper.findAll(selectors.selectedOptions)).toHaveLength(0);
    });

    it("reapplies the search when case sensitivity and regex modes change", async () => {
        const wrapper = mountSelectMany({ options: emailOptions(["foo", "BAR", "baz"]) });

        await search(wrapper, "bar");
        expect(wrapper.findAll(selectors.unselectedOptions)).toHaveLength(2);
        expect(wrapper.find(selectors.unselectedCount).text()).toBe("(2)");

        await wrapper.find(selectors.caseSensitivity).trigger("click");
        expect(wrapper.findAll(selectors.unselectedOptions)).toHaveLength(0);

        await search(wrapper, "BAR");
        expect(wrapper.findAll(selectors.unselectedOptions)).toHaveLength(2);

        await wrapper.find(selectors.useRegex).trigger("click");
        expect(wrapper.findAll(selectors.unselectedOptions)).toHaveLength(2);

        await search(wrapper, "^[a-z]+@");
        expect(wrapper.findAll(selectors.unselectedOptions)).toHaveLength(4);

        await wrapper.find(selectors.caseSensitivity).trigger("click");
        expect(wrapper.findAll(selectors.unselectedOptions)).toHaveLength(6);
    });

    it("selects and deselects only the options matching the current search", async () => {
        const wrapper = mountSelectMany({ options: emailOptions(["foo", "BAR", "baz"]) });

        await search(wrapper, "bar");
        await wrapper.find(selectors.selectAll).trigger("click");
        await applyInput(wrapper);
        await search(wrapper, "");
        expect(wrapper.findAll(selectors.selectedOptions)).toHaveLength(2);

        await search(wrapper, ".org");
        await wrapper.find(selectors.deselectAll).trigger("click");
        await applyInput(wrapper);
        await search(wrapper, "");
        expect(wrapper.findAll(selectors.selectedOptions)).toHaveLength(1);
    });

    it("applies shift and control highlights before moving options between columns", async () => {
        const wrapper = mountSelectMany({ options: emailOptions(["foo", "BAR", "baz", "bar"]) });
        const unselectedOptions = wrapper.findAll(selectors.unselectedOptions);

        await nth(unselectedOptions, 0).trigger("click", { shiftKey: true });
        await nth(unselectedOptions, 7).trigger("click", { shiftKey: true });
        expect(wrapper.findAll(selectors.unselectedHighlighted)).toHaveLength(8);

        await nth(unselectedOptions, 1).trigger("click", { ctrlKey: true });
        await nth(unselectedOptions, 2).trigger("click", { ctrlKey: true });
        expect(wrapper.findAll(selectors.unselectedHighlighted)).toHaveLength(6);

        await wrapper.find(selectors.selectAll).trigger("click");
        await applyInput(wrapper);
        const selectedOptions = wrapper.findAll(selectors.selectedOptions);
        expect(selectedOptions).toHaveLength(6);

        await nth(selectedOptions, 0).trigger("click", { shiftKey: true });
        await nth(selectedOptions, 5).trigger("click", { shiftKey: true });
        expect(wrapper.findAll(selectors.selectedHighlighted)).toHaveLength(6);

        await nth(selectedOptions, 2).trigger("click", { shiftKey: true, ctrlKey: true });
        await nth(selectedOptions, 5).trigger("click", { shiftKey: true, ctrlKey: true });
        expect(wrapper.findAll(selectors.selectedHighlighted)).toHaveLength(2);

        await wrapper.find(selectors.deselectAll).trigger("click");
        await applyInput(wrapper);
        expect(wrapper.findAll(selectors.unselectedOptions)).toHaveLength(4);
        expect(wrapper.findAll(selectors.selectedOptions)).toHaveLength(4);
    });
});

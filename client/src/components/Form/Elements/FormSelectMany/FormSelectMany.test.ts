import "./worker/__mocks__/selectMany";

import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/jest/helpers";
import { mount } from "@vue/test-utils";
import { type PropType } from "vue";

import { type SelectOption } from "./worker/selectMany";

import FormSelectMany from "./FormSelectMany.vue";

const pinia = createTestingPinia();
const localVue = getLocalVue();

jest.mock("@/components/Form/Elements/FormSelectMany/worker/selectMany");

function mountSelectMany(props: Partial<PropType<typeof FormSelectMany>>) {
    return mount(FormSelectMany as any, {
        propsData: { options: [], value: [], ...props },
        pinia,
        localVue,
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

function generateOptionsFromArrays(matrix: Array<Array<string>>): SelectOption[] {
    const combineTwo = (a: string[], b: string[]) => {
        const combined = [] as string[];

        a.forEach((aValue) => {
            b.forEach((bValue) => {
                combined.push(`${aValue}${bValue}`);
            });
        });

        return combined;
    };

    const combined = matrix.reduce((accumulator, current) => combineTwo(accumulator, current), [""]);

    return combined.map((v) => ({ label: v, value: v }));
}

/** gets the latest input event value and reflects it to props */
async function emittedInput(wrapper: ReturnType<typeof mountSelectMany>) {
    const emittedEvents = wrapper.emitted()?.["input"];

    if (!emittedEvents) {
        return undefined;
    }

    const latestValue = emittedEvents[emittedEvents.length - 1]?.[0];

    if (latestValue === undefined) {
        return undefined;
    }

    await wrapper.setProps({ ...wrapper.props(), value: latestValue });
    return latestValue;
}

// circumvent input debounce
jest.useFakeTimers();

async function search(wrapper: ReturnType<typeof mountSelectMany>, value: string) {
    const searchInput = wrapper.find(selectors.search);
    await searchInput.setValue(value);
    jest.runAllTimers();
}

describe("FormSelectMany", () => {
    it("displays all options", async () => {
        const options = generateOptionsFromArrays([["foo", "bar", "baz"], ["@"], ["galaxy"], [".com", ".org"]]);
        const wrapper = mountSelectMany({ options });

        const unselectedOptions = wrapper.findAll(selectors.unselectedOptions);
        expect(unselectedOptions.length).toBe(6);

        options.forEach((option, i) => {
            expect(unselectedOptions.at(i).text()).toBe(option.label);
        });
    });

    it("emits selected options", async () => {
        const options = generateOptionsFromArrays([["foo", "bar", "baz"], ["@"], ["galaxy"], [".com", ".org"]]);

        const wrapper = mountSelectMany({ options });

        {
            const firstOption = wrapper.findAll(selectors.unselectedOptions).at(0);
            await firstOption.trigger("click");

            const emitted = await emittedInput(wrapper);
            expect(emitted).toEqual(["foo@galaxy.com"]);
        }

        {
            const firstOption = wrapper.findAll(selectors.unselectedOptions).at(0);
            await firstOption.trigger("click");

            const emitted = await emittedInput(wrapper);
            expect(emitted).toEqual(["foo@galaxy.com", "foo@galaxy.org"]);
        }
    });

    it("displays selected values in the selected column", async () => {
        const options = generateOptionsFromArrays([["foo", "bar", "baz"], ["@"], ["galaxy"], [".com", ".org"]]);
        const wrapper = mountSelectMany({ options, value: ["foo@galaxy.com", "foo@galaxy.org"] });

        {
            const selectedOptions = wrapper.findAll(selectors.selectedOptions);
            expect(selectedOptions.length).toBe(2);
            expect(selectedOptions.at(0).text()).toBe("foo@galaxy.com");
            expect(selectedOptions.at(1).text()).toBe("foo@galaxy.org");

            const unselectedOptions = wrapper.findAll(selectors.unselectedOptions);
            unselectedOptions.wrappers.forEach((unselectedOption) => {
                expect(unselectedOption.text()).not.toBe("foo@galaxy.com");
                expect(unselectedOption.text()).not.toBe("foo@galaxy.org");
            });
        }

        const firstOption = wrapper.findAll(selectors.unselectedOptions).at(0);
        await firstOption.trigger("click");
        const emitted = await emittedInput(wrapper);

        {
            const selectedOptions = wrapper.findAll(selectors.selectedOptions);
            expect(selectedOptions.length).toBe(3);
            expect(selectedOptions.at(2).text()).toBe(emitted[2]);

            const unselectedOptions = wrapper.findAll(selectors.unselectedOptions);
            unselectedOptions.wrappers.forEach((unselectedOption) => {
                expect(unselectedOption.text()).not.toBe(emitted[2]);
            });
        }
    });

    it("shows the amount of selected options", async () => {
        const options = generateOptionsFromArrays([["foo", "bar", "baz"], ["@"], ["galaxy"], [".com", ".org"]]);
        const wrapper = mountSelectMany({ options, value: ["foo@galaxy.com", "foo@galaxy.org"] });

        {
            const selectedCount = wrapper.find(selectors.selectedCount);
            const unselectedCount = wrapper.find(selectors.unselectedCount);

            expect(selectedCount.text()).toBe("(2)");
            expect(unselectedCount.text()).toBe("(4)");
        }

        const firstOption = wrapper.findAll(selectors.unselectedOptions).at(0);
        await firstOption.trigger("click");
        await emittedInput(wrapper);

        {
            const selectedCount = wrapper.find(selectors.selectedCount);
            const unselectedCount = wrapper.find(selectors.unselectedCount);

            expect(selectedCount.text()).toBe("(3)");
            expect(unselectedCount.text()).toBe("(3)");
        }
    });

    it("selects all options", async () => {
        const options = generateOptionsFromArrays([["foo", "bar", "baz"], ["@"], ["galaxy"], [".com", ".org"]]);
        const wrapper = mountSelectMany({ options, value: ["foo@galaxy.com", "foo@galaxy.org"] });

        const selectAllButton = wrapper.find(selectors.selectAll);
        await selectAllButton.trigger("click");
        await emittedInput(wrapper);

        {
            const selectedOptions = wrapper.findAll(selectors.selectedOptions);
            const unselectedOptions = wrapper.findAll(selectors.unselectedOptions);

            expect(unselectedOptions.length).toBe(0);
            expect(selectedOptions.length).toBe(6);
        }

        const deselectAllButton = wrapper.find(selectors.deselectAll);
        await deselectAllButton.trigger("click");
        await emittedInput(wrapper);

        {
            const selectedOptions = wrapper.findAll(selectors.selectedOptions);
            const unselectedOptions = wrapper.findAll(selectors.unselectedOptions);

            expect(unselectedOptions.length).toBe(6);
            expect(selectedOptions.length).toBe(0);
        }
    });

    it("filters options", async () => {
        const options = generateOptionsFromArrays([["foo", "BAR", "baz"], ["@"], ["galaxy"], [".com", ".org"]]);
        const wrapper = mountSelectMany({ options });

        await search(wrapper, "bar");

        {
            const unselectedOptions = wrapper.findAll(selectors.unselectedOptions);
            expect(unselectedOptions.length).toBe(2);

            const unselectedCount = wrapper.find(selectors.unselectedCount);
            expect(unselectedCount.text()).toBe("(2)");
        }

        const caseSensitivityButton = wrapper.find(selectors.caseSensitivity);
        await caseSensitivityButton.trigger("click");

        {
            const unselectedOptions = wrapper.findAll(selectors.unselectedOptions);
            expect(unselectedOptions.length).toBe(0);
        }

        await search(wrapper, "BAR");

        {
            const unselectedOptions = wrapper.findAll(selectors.unselectedOptions);
            expect(unselectedOptions.length).toBe(2);
        }

        const useRegexButton = wrapper.find(selectors.useRegex);
        await useRegexButton.trigger("click");

        {
            const unselectedOptions = wrapper.findAll(selectors.unselectedOptions);
            expect(unselectedOptions.length).toBe(2);
        }

        await search(wrapper, "^[a-z]+@");

        {
            const unselectedOptions = wrapper.findAll(selectors.unselectedOptions);
            expect(unselectedOptions.length).toBe(4);
        }

        await caseSensitivityButton.trigger("click");

        {
            const unselectedOptions = wrapper.findAll(selectors.unselectedOptions);
            expect(unselectedOptions.length).toBe(6);
        }
    });

    it("selects filtered", async () => {
        const options = generateOptionsFromArrays([["foo", "BAR", "baz"], ["@"], ["galaxy"], [".com", ".org"]]);
        const wrapper = mountSelectMany({ options });

        await search(wrapper, "bar");

        const selectAllButton = wrapper.find(selectors.selectAll);
        await selectAllButton.trigger("click");
        await emittedInput(wrapper);

        await search(wrapper, "");

        {
            const selectedOptions = wrapper.findAll(selectors.selectedOptions);
            expect(selectedOptions.length).toBe(2);
        }

        await search(wrapper, ".org");

        const deselectAllButton = wrapper.find(selectors.deselectAll);
        await deselectAllButton.trigger("click");
        await emittedInput(wrapper);

        await search(wrapper, "");

        {
            const selectedOptions = wrapper.findAll(selectors.selectedOptions);
            expect(selectedOptions.length).toBe(1);
        }
    });

    it("allows for highlighting ranges", async () => {
        const options = generateOptionsFromArrays([["foo", "BAR", "baz", "bar"], ["@"], ["galaxy"], [".com", ".org"]]);
        const wrapper = mountSelectMany({ options });

        {
            const unselectedOptions = wrapper.findAll(selectors.unselectedOptions);
            await unselectedOptions.at(0).trigger("click", { shiftKey: true });
            await unselectedOptions.at(7).trigger("click", { shiftKey: true });

            {
                const highlightedOptions = wrapper.findAll(selectors.unselectedHighlighted);
                expect(highlightedOptions.length).toBe(8);
            }

            await unselectedOptions.at(1).trigger("click", { ctrlKey: true });
            await unselectedOptions.at(2).trigger("click", { ctrlKey: true });

            {
                const highlightedOptions = wrapper.findAll(selectors.unselectedHighlighted);
                expect(highlightedOptions.length).toBe(6);
            }
        }

        const selectAllButton = wrapper.find(selectors.selectAll);
        await selectAllButton.trigger("click");
        await emittedInput(wrapper);

        {
            const selectedOptions = wrapper.findAll(selectors.selectedOptions);
            expect(selectedOptions.length).toBe(6);

            await selectedOptions.at(0).trigger("click", { shiftKey: true });
            await selectedOptions.at(5).trigger("click", { shiftKey: true });

            {
                const highlightedOptions = wrapper.findAll(selectors.selectedHighlighted);
                expect(highlightedOptions.length).toBe(6);
            }

            await selectedOptions.at(2).trigger("click", { shiftKey: true, ctrlKey: true });
            await selectedOptions.at(5).trigger("click", { shiftKey: true, ctrlKey: true });

            {
                const highlightedOptions = wrapper.findAll(selectors.selectedHighlighted);
                expect(highlightedOptions.length).toBe(2);
            }
        }

        const deselectAllButton = wrapper.find(selectors.deselectAll);
        await deselectAllButton.trigger("click");
        await emittedInput(wrapper);

        {
            const unselectedOptions = wrapper.findAll(selectors.unselectedOptions);
            expect(unselectedOptions.length).toBe(4);

            const selectedOptions = wrapper.findAll(selectors.selectedOptions);
            expect(selectedOptions.length).toBe(4);
        }
    });
});

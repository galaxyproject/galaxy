import { getLocalVue } from "@tests/jest/helpers";
import { mount } from "@vue/test-utils";
import { nextTick } from "vue";

import HeadlessMultiselect from "./HeadlessMultiselect.vue";

describe("HeadlessMultiselect", () => {
    // this function is not implemented in jsdom
    // mocking it to avoid false errors
    Element.prototype.scrollIntoView = jest.fn();

    const localVue = getLocalVue();

    // Define props type based on the component's prop definitions
    type Props = {
        options: Array<string>;
        selected: Array<string>;
        maxShownOptions?: number;
        placeholder?: string;
        id?: string;
        validator?: (option: string) => boolean;
    };
    const mountWithProps = (props: Props) => {
        return mount(HeadlessMultiselect as any, {
            props,
            global: localVue.global,
            attachTo: document.body,
        });
    };

    const sampleOptions = ["name:named", "name:named_2", "name:named_3", "abc", "def", "ghi"];

    const selectors = {
        openButton: ".toggle-button",
        option: ".headless-multiselect__option",
        highlighted: ".headless-multiselect__option.highlighted",
        input: "fieldset input",
        invalid: ".headless-multiselect__option.invalid",
    } as const;

    // Accept both VueWrapper and DOMWrapper for keyboard events
    async function keyPress(element: any, key: string) {
        element.trigger("keydown", {
            key,
            code: key,
        });
        await nextTick();
        element.trigger("keyup", {
            key,
            code: key,
        });
        await nextTick();
    }

    async function open(wrapper: ReturnType<typeof mountWithProps>) {
        wrapper.find(selectors.openButton).trigger("click");
        await nextTick();
        return wrapper.find(selectors.input);
    }

    async function close(wrapper: ReturnType<typeof mountWithProps>) {
        await keyPress(wrapper.find(selectors.input), "Escape");
    }

    describe("while toggling the popup", () => {
        it("shows and hides options", async () => {
            const wrapper = mountWithProps({
                options: sampleOptions,
                selected: [] as string[],
            });

            let options;

            await open(wrapper);
            options = wrapper.findAll(selectors.option);
            expect(options.length).toBe(sampleOptions.length);

            await close(wrapper);
            options = wrapper.findAll(selectors.option);
            expect(options.length).toBe(0);
        });

        it("retains focus", async () => {
            const wrapper = mountWithProps({
                options: sampleOptions,
                selected: [] as string[],
            });

            const input = await open(wrapper);
            expect(input.element).toBe(document.activeElement);

            await close(wrapper);
            const button = wrapper.find(selectors.openButton);
            expect(button.element).toBe(document.activeElement);
        });
    });

    describe("while inputting text", () => {
        it("filters options", async () => {
            const wrapper = mountWithProps({
                options: sampleOptions,
                selected: [] as string[],
            });

            let options;

            const input = await open(wrapper);

            await input.setValue("a");
            options = wrapper.findAll(selectors.option);
            expect(options.length).toBe(5);

            await input.setValue("na");
            options = wrapper.findAll(selectors.option);
            expect(options.length).toBe(4);

            await input.setValue("");
            options = wrapper.findAll(selectors.option);
            expect(options.length).toBe(6);
        });

        it("shows the search value on top", async () => {
            const wrapper = mountWithProps({
                options: sampleOptions,
                selected: [] as string[],
            });

            const input = await open(wrapper);

            await input.setValue("bc");
            const options = wrapper.findAll(selectors.option);

            expect(options[0]!.find("span").text()).toBe("bc");
            expect(options[1]!.find("span").text()).toBe("abc");

            await close(wrapper);
        });

        it("allows for switching the highlighted value", async () => {
            const wrapper = mountWithProps({
                options: sampleOptions,
                selected: [] as string[],
            });

            let highlighted;

            const input = await open(wrapper);

            highlighted = wrapper.find(selectors.highlighted);
            expect(highlighted.find("span").text()).toBe("#named");

            await keyPress(input, "ArrowDown");
            highlighted = wrapper.find(selectors.highlighted);
            expect(highlighted.find("span").text()).toBe("#named_2");

            await keyPress(input, "ArrowDown");
            highlighted = wrapper.find(selectors.highlighted);
            expect(highlighted.find("span").text()).toBe("#named_3");

            await keyPress(input, "ArrowUp");
            highlighted = wrapper.find(selectors.highlighted);
            expect(highlighted.find("span").text()).toBe("#named_2");

            await close(wrapper);
        });

        it("resets the highlighted option on input", async () => {
            const wrapper = mountWithProps({
                options: sampleOptions,
                selected: [] as string[],
            });

            let highlighted;

            const input = await open(wrapper);

            await keyPress(input, "ArrowDown");
            highlighted = wrapper.find(selectors.highlighted);
            expect(highlighted.find("span").text()).toBe("#named_2");

            await input.setValue("a");

            highlighted = wrapper.find(selectors.highlighted);
            expect(highlighted.find("span").text()).toBe("a");

            await close(wrapper);
        });

        it("shows if the input value is valid", async () => {
            const wrapper = mountWithProps({
                options: sampleOptions,
                selected: [] as string[],
                validator: (value: string) => value !== "invalid",
            });

            const input = await open(wrapper);
            await input.setValue("valid");
            expect(() => wrapper.get(selectors.invalid)).toThrow();

            await input.setValue("invalid");
            expect(() => wrapper.get(selectors.invalid)).not.toThrow();
            await close(wrapper);
        });
    });

    describe("when selecting options", () => {
        it("selects options via keyboard", async () => {
            const wrapper = mountWithProps({
                options: sampleOptions,
                selected: [] as string[],
            });

            const input = await open(wrapper);

            await keyPress(input, "Enter");
            const emitted = wrapper.emitted() as Record<string, unknown[][]>;
            expect(emitted.input?.[0]?.[0]).toEqual(["name:named"]);

            await keyPress(input, "ArrowDown");
            await keyPress(input, "Enter");
            expect(emitted.input?.[1]?.[0]).toEqual(["name:named_2"]);
            await close(wrapper);
        });

        it("deselects options via keyboard", async () => {
            const wrapper = mountWithProps({
                options: sampleOptions,
                selected: ["name:named", "name:named_2", "name:named_3"],
            });

            const input = await open(wrapper);

            await keyPress(input, "Enter");
            const emitted = wrapper.emitted() as Record<string, unknown[][]>;
            expect(emitted.input?.[0]?.[0]).toEqual(["name:named_2", "name:named_3"]);

            await keyPress(input, "ArrowDown");
            await keyPress(input, "Enter");
            expect(emitted.input?.[1]?.[0]).toEqual(["name:named", "name:named_3"]);
            await close(wrapper);
        });

        it("allows for adding new options", async () => {
            const wrapper = mountWithProps({
                options: sampleOptions,
                selected: [] as string[],
            });

            const input = await open(wrapper);
            await input.setValue("123");
            await keyPress(input, "Enter");

            const emitted = wrapper.emitted() as Record<string, unknown[][]>;
            expect(emitted.addOption?.[0]?.[0]).toBe("123");
            await close(wrapper);
        });

        it("selects options with mouse", async () => {
            const wrapper = mountWithProps({
                options: sampleOptions,
                selected: [] as string[],
            });

            await open(wrapper);
            const options = wrapper.findAll(selectors.option);

            await options[0]!.trigger("click");
            const emitted = wrapper.emitted() as Record<string, unknown[][]>;
            expect(emitted.input?.[0]?.[0]).toEqual(["name:named"]);

            await options[1]!.trigger("click");
            expect(emitted.input?.[1]?.[0]).toEqual(["name:named_2"]);
            await close(wrapper);
        });

        it("deselects options with mouse", async () => {
            const wrapper = mountWithProps({
                options: sampleOptions,
                selected: ["name:named", "name:named_2", "name:named_3"],
            });

            await open(wrapper);
            const options = wrapper.findAll(selectors.option);

            await options[0]!.trigger("click");
            const emitted = wrapper.emitted() as Record<string, unknown[][]>;
            expect(emitted.input?.[0]?.[0]).toEqual(["name:named_2", "name:named_3"]);

            await options[1]!.trigger("click");
            expect(emitted.input?.[1]?.[0]).toEqual(["name:named", "name:named_3"]);
            await close(wrapper);
        });
    });
});

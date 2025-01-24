import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import { nextTick } from "vue";

import HeadlessMultiselect from "./HeadlessMultiselect.vue";

describe("HeadlessMultiselect", () => {
    // this function is not implemented in jsdom
    // mocking it to avoid false errors
    Element.prototype.scrollIntoView = jest.fn();

    const localVue = getLocalVue();

    type Props = InstanceType<typeof HeadlessMultiselect>["$props"];
    const mountWithProps = (props: Props) => {
        return mount(HeadlessMultiselect as any, {
            propsData: props,
            localVue,
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

    async function keyPress(wrapper: ReturnType<typeof mountWithProps>, key: string) {
        wrapper.trigger("keydown", {
            key,
            code: key,
        });
        await nextTick();
        wrapper.trigger("keyup", {
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

            expect(options.at(0).find("span").text()).toBe("bc");
            expect(options.at(1).find("span").text()).toBe("abc");
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
            expect(wrapper.emitted()["input"]?.[0]?.[0]).toEqual(["name:named"]);

            await keyPress(input, "ArrowDown");
            await keyPress(input, "Enter");
            expect(wrapper.emitted()["input"]?.[1]?.[0]).toEqual(["name:named_2"]);
        });

        it("deselects options via keyboard", async () => {
            const wrapper = mountWithProps({
                options: sampleOptions,
                selected: ["name:named", "name:named_2", "name:named_3"],
            });

            const input = await open(wrapper);

            await keyPress(input, "Enter");
            expect(wrapper.emitted()["input"]?.[0]?.[0]).toEqual(["name:named_2", "name:named_3"]);

            await keyPress(input, "ArrowDown");
            await keyPress(input, "Enter");
            expect(wrapper.emitted()["input"]?.[1]?.[0]).toEqual(["name:named", "name:named_3"]);
        });

        it("allows for adding new options", async () => {
            const wrapper = mountWithProps({
                options: sampleOptions,
                selected: [] as string[],
            });

            const input = await open(wrapper);
            await input.setValue("123");
            await keyPress(input, "Enter");

            expect(wrapper.emitted()["addOption"]?.[0]?.[0]).toBe("123");
        });

        it("selects options with mouse", async () => {
            const wrapper = mountWithProps({
                options: sampleOptions,
                selected: [] as string[],
            });

            await open(wrapper);
            const options = wrapper.findAll(selectors.option);

            await options.at(0).trigger("click");
            expect(wrapper.emitted()["input"]?.[0]?.[0]).toEqual(["name:named"]);

            await options.at(1).trigger("click");
            expect(wrapper.emitted()["input"]?.[1]?.[0]).toEqual(["name:named_2"]);
        });

        it("deselects options with mouse", async () => {
            const wrapper = mountWithProps({
                options: sampleOptions,
                selected: ["name:named", "name:named_2", "name:named_3"],
            });

            await open(wrapper);
            const options = wrapper.findAll(selectors.option);

            await options.at(0).trigger("click");
            expect(wrapper.emitted()["input"]?.[0]?.[0]).toEqual(["name:named_2", "name:named_3"]);

            await options.at(1).trigger("click");
            expect(wrapper.emitted()["input"]?.[1]?.[0]).toEqual(["name:named", "name:named_3"]);
        });
    });
});

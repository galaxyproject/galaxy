import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import { defineComponent, nextTick, ref } from "vue";

import GProgress from "./GProgress.vue";
import GProgressBar from "./GProgressBar.vue";

function mountStacked(template: string) {
    return mount(defineComponent({ components: { GProgress, GProgressBar }, template }));
}

function bars(wrapper: ReturnType<typeof mount>) {
    return wrapper.findAll('[role="progressbar"]');
}

describe("GProgress", () => {
    it("renders one progressbar with its value range", () => {
        const wrapper = mount(GProgress, { props: { value: 30, max: 120 } });
        const [bar] = bars(wrapper);

        expect(bars(wrapper)).toHaveLength(1);
        expect(bar!.attributes("aria-valuemin")).toBe("0");
        expect(bar!.attributes("aria-valuemax")).toBe("120");
        expect(bar!.attributes("aria-valuenow")).toBe("30");
        expect(bar!.attributes("style")).toContain("width: 25%");
    });

    it("defaults the maximum to 100 and accepts numeric strings", () => {
        const wrapper = mount(GProgress, { props: { value: "40", max: "100" } });

        expect(bars(wrapper)[0]!.attributes("aria-valuemax")).toBe("100");
        expect(bars(wrapper)[0]!.attributes("aria-valuenow")).toBe("40");
        expect(
            mount(GProgress, { props: { value: 5 } })
                .get('[role="progressbar"]')
                .attributes("aria-valuemax"),
        ).toBe("100");
    });

    it("keeps the bar and its announced value within the range", () => {
        const over = mount(GProgress, { props: { value: 150 } }).get('[role="progressbar"]');
        expect(over.attributes("style")).toContain("width: 100%");
        expect(over.attributes("aria-valuenow")).toBe("100");

        const under = mount(GProgress, { props: { value: -5 } }).get('[role="progressbar"]');
        expect(under.attributes("style")).toContain("width: 0%");
        expect(under.attributes("aria-valuenow")).toBe("0");
    });

    it("names the single bar with the label given to the progress", () => {
        const wrapper = mount(GProgress, { props: { value: 10, ariaLabel: "Upload progress" } });

        expect(wrapper.get('[role="progressbar"]').attributes("aria-label")).toBe("Upload progress");
        expect(wrapper.attributes("aria-label")).toBeUndefined();
        expect(wrapper.attributes("role")).toBeUndefined();
    });

    it("points the single bar at an external label", () => {
        const wrapper = mount(GProgress, { props: { value: 10, ariaLabelledby: "upload-heading" } });

        expect(wrapper.get('[role="progressbar"]').attributes("aria-labelledby")).toBe("upload-heading");
    });

    it("shows the percentage by default, to the given precision", () => {
        expect(mount(GProgress, { props: { value: 1, max: 3 } }).text()).toBe("33%");
        expect(mount(GProgress, { props: { value: 1, max: 3, precision: 1 } }).text()).toBe("33.3%");
    });

    it("shows the percentage on stacked bars by default", () => {
        const wrapper = mountStacked(`
            <GProgress :max="10">
                <GProgressBar :value="2" />
                <GProgressBar :value="5" />
            </GProgress>`);

        expect(bars(wrapper).map((bar) => bar.text())).toEqual(["20%", "50%"]);
    });

    it("shows no text with showProgress set to false, on the progress or on a bar", () => {
        expect(mount(GProgress, { props: { value: 50, showProgress: false } }).text()).toBe("");
        expect(mount(GProgressBar, { props: { value: 50, showProgress: false } }).text()).toBe("");
    });

    it("shows the raw value with showValue", () => {
        expect(mount(GProgress, { props: { value: 7, max: 20, showValue: true } }).text()).toBe("7");
    });

    it("shows a label and announces it as the value text", () => {
        const wrapper = mount(GProgress, { props: { value: 3, max: 10, label: "3 of 10 files" } });

        expect(wrapper.text()).toBe("3 of 10 files");
        expect(wrapper.get('[role="progressbar"]').attributes("aria-valuetext")).toBe("3 of 10 files");
    });

    it("stacks bars against the progress maximum", () => {
        const wrapper = mountStacked(`
            <GProgress :max="10" aria-label="Job states">
                <GProgressBar :value="2" aria-label="Failed" />
                <GProgressBar :value="5" aria-label="Done" />
            </GProgress>`);
        const [failed, done] = bars(wrapper);

        expect(bars(wrapper)).toHaveLength(2);
        expect(failed!.attributes("aria-valuemax")).toBe("10");
        expect(failed!.attributes("style")).toContain("width: 20%");
        expect(done!.attributes("style")).toContain("width: 50%");
        expect(done!.attributes("aria-label")).toBe("Done");
    });

    it("groups stacked bars under the progress label", () => {
        const wrapper = mountStacked(`
            <GProgress :max="10" aria-label="Job states">
                <GProgressBar :value="2" />
            </GProgress>`);
        const root = wrapper.get(".g-progress");

        expect(root.attributes("role")).toBe("group");
        expect(root.attributes("aria-label")).toBe("Job states");
    });

    it("updates the track's role when its stacked content comes and goes", async () => {
        const showBars = ref(false);
        const wrapper = mount(
            defineComponent({
                components: { GProgress, GProgressBar },
                setup: () => ({ showBars }),
                template: `
                    <GProgress :value="3" aria-label="Job states">
                        <template v-if="showBars" #default>
                            <GProgressBar :value="2" aria-label="Failed" />
                        </template>
                    </GProgress>`,
            }),
        );
        const root = () => wrapper.get(".g-progress");

        expect(root().attributes("role")).toBeUndefined();

        showBars.value = true;
        await nextTick();
        expect(root().attributes("role")).toBe("group");
        expect(root().attributes("aria-label")).toBe("Job states");

        showBars.value = false;
        await nextTick();
        expect(root().attributes("role")).toBeUndefined();
        expect(bars(wrapper)[0]!.attributes("aria-label")).toBe("Job states");
    });

    it("follows a changing value", async () => {
        const wrapper = mount(GProgress, { props: { value: 20 } });

        await wrapper.setProps({ value: 60 });

        const bar = wrapper.get('[role="progressbar"]');
        expect(bar.attributes("aria-valuenow")).toBe("60");
        expect(bar.attributes("style")).toContain("width: 60%");
    });

    it("updates stacked bars when the progress maximum or display options change", async () => {
        const max = ref(10);
        const showProgress = ref(false);
        const wrapper = mount(
            defineComponent({
                components: { GProgress, GProgressBar },
                setup: () => ({ max, showProgress }),
                template: `
                    <GProgress :max="max" :show-progress="showProgress">
                        <GProgressBar :value="2" />
                    </GProgress>`,
            }),
        );

        max.value = 4;
        showProgress.value = true;
        await nextTick();

        const bar = wrapper.get('[role="progressbar"]');
        expect(bar.attributes("aria-valuemax")).toBe("4");
        expect(bar.attributes("style")).toContain("width: 50%");
        expect(bar.text()).toBe("50%");
    });

    it("lets a bar override the progress maximum", () => {
        const wrapper = mountStacked(`
            <GProgress :max="10">
                <GProgressBar :value="2" :max="4" />
            </GProgress>`);

        expect(bars(wrapper)[0]!.attributes("aria-valuemax")).toBe("4");
        expect(bars(wrapper)[0]!.attributes("style")).toContain("width: 50%");
    });

    it("lets bars take display options from the progress unless they set their own", () => {
        const wrapper = mountStacked(`
            <GProgress :max="4" show-progress>
                <GProgressBar :value="1" />
                <GProgressBar :value="2" :show-progress="false" />
            </GProgress>`);
        const [inherits, own] = bars(wrapper);

        expect(inherits!.text()).toBe("25%");
        expect(own!.text()).toBe("");
    });

    it("lets a bar's own showProgress win over the progress's showValue", () => {
        const wrapper = mountStacked(`
            <GProgress :max="4" show-value>
                <GProgressBar :value="1" />
                <GProgressBar :value="2" show-progress />
                <GProgressBar :value="3" show-progress show-value />
            </GProgress>`);

        expect(bars(wrapper).map((bar) => bar.text())).toEqual(["1", "50%", "3"]);
    });

    it("passes attributes such as data-* and title to the bar element", () => {
        const wrapper = mountStacked(`
            <GProgress :max="4">
                <GProgressBar :value="1" data-description="error count" title="1 Error" />
            </GProgress>`);

        expect(bars(wrapper)[0]!.attributes("data-description")).toBe("error count");
        expect(bars(wrapper)[0]!.attributes("title")).toBe("1 Error");
    });

    it("renders custom bar content from the default slot", () => {
        const wrapper = mountStacked(`
            <GProgress :max="4">
                <GProgressBar :value="1"><strong>one</strong></GProgressBar>
            </GProgress>`);

        expect(wrapper.get('[role="progressbar"] strong').text()).toBe("one");
    });

    it("marks the fill end of a bar without a value only when its fill is below 3:1 against the track", () => {
        const marked = (props: object) =>
            mount(GProgressBar, { props: { value: 40, showProgress: false, ...props } }).classes(
                "g-progress-bar-marked",
            );

        for (const variant of ["success", "warning", "info"] as const) {
            expect(marked({ variant })).toBe(true);
        }
        for (const variant of ["primary", "secondary", "danger", "dark"] as const) {
            expect(marked({ variant })).toBe(false);
        }
    });

    it("leaves the fill end unmarked when the bar has content or no fill", () => {
        const options = { props: { value: 40, variant: "success" as const } };

        expect(mount(GProgressBar, options).classes("g-progress-bar-marked")).toBe(false);
        expect(
            mount(GProgressBar, { props: { ...options.props, showProgress: false, label: "Four" } }).classes(
                "g-progress-bar-marked",
            ),
        ).toBe(false);
        expect(
            mount(GProgressBar, {
                props: { ...options.props, showProgress: false },
                slots: { default: "Four" },
            }).classes("g-progress-bar-marked"),
        ).toBe(false);
        expect(
            mount(GProgressBar, { props: { variant: "success", value: 0, showProgress: false } }).classes(
                "g-progress-bar-marked",
            ),
        ).toBe(false);
    });

    it("leaves a full bar unmarked, since its fill has no end to mark", () => {
        for (const value of [100, 150]) {
            const options = { props: { value, variant: "success" as const, showProgress: false } };

            expect(mount(GProgressBar, options).classes("g-progress-bar-marked")).toBe(false);
        }
        const nearlyFull = { props: { value: 99, variant: "success" as const, showProgress: false } };
        expect(mount(GProgressBar, nearlyFull).classes("g-progress-bar-marked")).toBe(true);
    });

    it("drops the percentage below 5% of the maximum and marks the fill end instead", () => {
        const narrow = mount(GProgressBar, { props: { value: 49, max: 1000, variant: "success" } });
        expect(narrow.text()).toBe("");
        expect(narrow.classes("g-progress-bar-marked")).toBe(true);
        expect(narrow.attributes("aria-valuenow")).toBe("49");
        expect(narrow.attributes("aria-valuemax")).toBe("1000");

        const atLimit = mount(GProgressBar, { props: { value: 5, variant: "success" } });
        expect(atLimit.text()).toBe("5%");
        expect(atLimit.classes("g-progress-bar-marked")).toBe(false);

        const stacked = mountStacked(`
            <GProgress :max="100" show-progress>
                <GProgressBar :value="3" variant="warning" />
                <GProgressBar :value="20" variant="warning" />
            </GProgress>`);
        expect(bars(stacked).map((bar) => bar.text())).toEqual(["", "20%"]);
    });

    it("keeps explicit content on a narrow fill", () => {
        const options = { value: 1, variant: "success" as const };

        const labelled = mount(GProgressBar, { props: { ...options, label: "One" } });
        expect(labelled.text()).toBe("One");
        expect(labelled.classes("g-progress-bar-marked")).toBe(false);

        const slotted = mount(GProgressBar, { props: options, slots: { default: "One" } });
        expect(slotted.text()).toBe("One");
        expect(slotted.classes("g-progress-bar-marked")).toBe(false);

        expect(mount(GProgressBar, { props: { ...options, showValue: true } }).text()).toBe("1");
    });

    it("renders no content in a bar with no fill", () => {
        for (const props of [{}, { showValue: true }, { label: "None" }]) {
            expect(mount(GProgressBar, { props: { value: 0, ...props } }).text()).toBe("");
        }
        expect(mount(GProgressBar, { props: { value: 0 }, slots: { default: "None" } }).text()).toBe("");
        expect(mount(GProgressBar, { props: { value: 0, label: "None" } }).attributes("aria-valuetext")).toBe("None");
    });

    it("works as a standalone bar with a maximum of 100", () => {
        const wrapper = mount(GProgressBar, { props: { value: 40 } });

        expect(wrapper.attributes("role")).toBe("progressbar");
        expect(wrapper.attributes("aria-valuemax")).toBe("100");
        expect(wrapper.attributes("style")).toContain("width: 40%");
    });
});

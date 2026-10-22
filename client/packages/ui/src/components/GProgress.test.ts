import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import { defineComponent } from "vue";

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

    it("keeps the bar within the track", () => {
        expect(
            mount(GProgress, { props: { value: 150 } })
                .get('[role="progressbar"]')
                .attributes("style"),
        ).toContain("width: 100%");
        expect(
            mount(GProgress, { props: { value: -5 } })
                .get('[role="progressbar"]')
                .attributes("style"),
        ).toContain("width: 0%");
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

    it("shows the percentage with showProgress, to the given precision", () => {
        expect(mount(GProgress, { props: { value: 1, max: 3, showProgress: true } }).text()).toBe("33");
        expect(mount(GProgress, { props: { value: 1, max: 3, showProgress: true, precision: 1 } }).text()).toBe("33.3");
    });

    it("shows the raw value with showValue", () => {
        expect(mount(GProgress, { props: { value: 7, max: 20, showValue: true } }).text()).toBe("7");
    });

    it("shows a label and announces it as the value text", () => {
        const wrapper = mount(GProgress, { props: { value: 3, max: 10, label: "3 of 10 files" } });

        expect(wrapper.text()).toBe("3 of 10 files");
        expect(wrapper.get('[role="progressbar"]').attributes("aria-valuetext")).toBe("3 of 10 files");
    });

    it("shows no text by default", () => {
        expect(mount(GProgress, { props: { value: 50 } }).text()).toBe("");
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

        expect(inherits!.text()).toBe("25");
        expect(own!.text()).toBe("");
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

    it("works as a standalone bar with a maximum of 100", () => {
        const wrapper = mount(GProgressBar, { props: { value: 40 } });

        expect(wrapper.attributes("role")).toBe("progressbar");
        expect(wrapper.attributes("aria-valuemax")).toBe("100");
        expect(wrapper.attributes("style")).toContain("width: 40%");
    });
});

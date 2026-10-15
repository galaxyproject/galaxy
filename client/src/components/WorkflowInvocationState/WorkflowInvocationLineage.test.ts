import { shallowMount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import WorkflowInvocationLineage from "./WorkflowInvocationLineage.vue";

function mountLineage(source: string | null, latest: string | null) {
    return shallowMount(WorkflowInvocationLineage, {
        props: { invocation: { rerun_of_invocation_id: source, latest_rerun_invocation_id: latest } },
        global: {
            stubs: {
                GAlert: { template: "<div><slot /></div>" },
                RouterLink: { props: ["to"], template: '<a :href="to"><slot /></a>' },
            },
        },
    });
}

describe("WorkflowInvocationLineage", () => {
    it("hides lineage for an original invocation without reruns", () => {
        const wrapper = mountLineage(null, null);
        expect(wrapper.find("a").exists()).toBe(false);
        expect(wrapper.text()).toBe("");
    });

    it("links back to the source invocation", () => {
        const wrapper = mountLineage("source-id", null);
        expect(wrapper.text()).toContain("This invocation is a rerun");
        expect(wrapper.get('[data-description="source invocation link"]').attributes("href")).toBe(
            "/workflows/invocations/source-id",
        );
        expect(wrapper.find('[data-description="latest rerun invocation link"]').exists()).toBe(false);
    });

    it("links to both neighbors for an invocation that was rerun again", () => {
        const wrapper = mountLineage("source-id", "newer-id");
        expect(wrapper.text()).toContain("A newer rerun of this invocation exists");
        expect(wrapper.get('[data-description="latest rerun invocation link"]').attributes("href")).toBe(
            "/workflows/invocations/newer-id",
        );
        expect(wrapper.find('[data-description="source invocation link"]').exists()).toBe(true);
    });
});

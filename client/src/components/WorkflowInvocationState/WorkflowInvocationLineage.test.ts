import { getLocalVue } from "@tests/vitest/helpers";
import { mount, RouterLinkStub } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import WorkflowInvocationLineage from "./WorkflowInvocationLineage.vue";
import GAlert from "@/components/BaseComponents/GAlert.vue";

const localVue = getLocalVue();

const SOURCE_ROUTE = "/workflows/invocations/source-id";
const LATEST_ROUTE = "/workflows/invocations/latest-id";

function mountLineage(lineage: Record<string, string | null>, compact?: boolean) {
    return mount(WorkflowInvocationLineage as object, {
        props: { invocation: lineage, compact },
        global: { ...localVue, stubs: { RouterLink: RouterLinkStub } },
    });
}

function linkRoutes(wrapper: ReturnType<typeof mountLineage>) {
    return wrapper.findAllComponents(RouterLinkStub).map((link) => link.props("to"));
}

describe("WorkflowInvocationLineage", () => {
    const bothLinks = { rerun_of_invocation_id: "source-id", latest_rerun_invocation_id: "latest-id" };

    it("shows one banner per link by default", () => {
        const wrapper = mountLineage(bothLinks);
        expect(wrapper.findAllComponents(GAlert).length).toBe(2);
        expect(linkRoutes(wrapper)).toEqual([SOURCE_ROUTE, LATEST_ROUTE]);
    });

    it("shows both links on one line without banners when compact", () => {
        const wrapper = mountLineage(bothLinks, true);
        expect(wrapper.findComponent(GAlert).exists()).toBe(false);
        expect(linkRoutes(wrapper)).toEqual([SOURCE_ROUTE, LATEST_ROUTE]);
        expect(wrapper.text()).toContain("·");
    });

    it("shows only the available link and no separator when compact", () => {
        const sourceOnly = mountLineage({ rerun_of_invocation_id: "source-id" }, true);
        expect(linkRoutes(sourceOnly)).toEqual([SOURCE_ROUTE]);
        expect(sourceOnly.text()).not.toContain("·");

        const latestOnly = mountLineage({ latest_rerun_invocation_id: "latest-id" }, true);
        expect(linkRoutes(latestOnly)).toEqual([LATEST_ROUTE]);
        expect(latestOnly.text()).not.toContain("·");
    });

    it.each([false, true])("renders nothing without lineage (compact: %s)", (compact) => {
        expect(mountLineage({}, compact).text()).toBe("");
    });
});

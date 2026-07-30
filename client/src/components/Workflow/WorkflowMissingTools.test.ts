import { getLocalVue } from "@tests/vitest/helpers";
import { mount, type Wrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { getWorkflowToolAvailability, installWorkflowTools, requestWorkflowToolInstallation } from "@/api/workflows";

import WorkflowMissingTools from "./WorkflowMissingTools.vue";
import GButton from "@/components/BaseComponents/GButton.vue";

vi.mock("@/api/workflows", () => ({
    getWorkflowToolAvailability: vi.fn(),
    installWorkflowTools: vi.fn(),
    requestWorkflowToolInstallation: vi.fn(),
}));

const localVue = getLocalVue();
const WORKFLOW_ID = "wf1";

function shedTool(
    name: string,
    wanted: string,
    installed: string[] = [],
    substitute: string | null = null,
    tool = `${name}_tool`,
) {
    return {
        tool_id: `toolshed.g2.bx.psu.edu/repos/bgruening/${name}/${tool}/${wanted}`,
        tool_version: wanted,
        installed_versions: installed,
        substitute_version: substitute,
        repository: { tool_shed: "toolshed.g2.bx.psu.edu", owner: "bgruening", name },
    };
}

function availability(tools: unknown[], canInstall = true) {
    return {
        unavailable_tools: tools,
        can_install: canInstall,
        cannot_install_reason: canInstall ? null : "Only administrators can install tools.",
    };
}

function mountDialog(): Wrapper<Vue> {
    // mounted rather than shallow: the actions live in a slot of the modal, which a stub drops
    return mount(WorkflowMissingTools as object, {
        propsData: { workflowId: WORKFLOW_ID, show: true },
        localVue,
    });
}

function buttonWith(wrapper: Wrapper<Vue>, text: string) {
    return wrapper.findAllComponents(GButton).filter((button) => button.text().includes(text));
}

describe("WorkflowMissingTools", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        vi.mocked(installWorkflowTools).mockResolvedValue({ installed: [], failed: [] } as never);
    });

    it("lists what is missing and what the workflow wanted", async () => {
        vi.mocked(getWorkflowToolAvailability).mockResolvedValue(
            availability([shedTool("text_processing", "9.3+galaxy1")]) as never,
        );
        const wrapper = mountDialog();
        await flushPromises();
        expect(wrapper.text()).toContain("9.3+galaxy1");
        expect(wrapper.text()).toContain("not installed");
    });

    it("distinguishes a safe stand-in from a version it cannot vouch for", async () => {
        vi.mocked(getWorkflowToolAvailability).mockResolvedValue(
            availability([
                shedTool("safe_one", "1.0", ["1.1"], "1.1"),
                shedTool("risky_one", "9.3+galaxy1", ["9.5+galaxy3"]),
            ]) as never,
        );
        const wrapper = mountDialog();
        await flushPromises();
        expect(wrapper.text()).toContain("1.1 installed, a safe stand-in");
        expect(wrapper.text()).toContain("only 9.5+galaxy3 installed");
    });

    it("offers to switch whenever another version is here, not only when it is vouched for", async () => {
        vi.mocked(getWorkflowToolAvailability).mockResolvedValue(
            availability([shedTool("risky_one", "9.3+galaxy1", ["9.5+galaxy3"])]) as never,
        );
        const wrapper = mountDialog();
        await flushPromises();
        expect(buttonWith(wrapper, "Switch to the installed versions").length).toBe(1);
        // and it says which of the two choices is which
        expect(wrapper.text()).toContain("Installing gets the exact versions");
    });

    it("does not offer to switch when nothing of the tool is installed", async () => {
        vi.mocked(getWorkflowToolAvailability).mockResolvedValue(
            availability([shedTool("text_processing", "9.3+galaxy1")]) as never,
        );
        const wrapper = mountDialog();
        await flushPromises();
        expect(buttonWith(wrapper, "Switch to the installed versions").length).toBe(0);
    });

    it("installs one repository at a time, so progress can be shown", async () => {
        vi.mocked(getWorkflowToolAvailability).mockResolvedValue(
            availability([shedTool("text_processing", "9.3+galaxy1"), shedTool("fastp", "0.24.3+galaxy0")]) as never,
        );
        const wrapper = mountDialog();
        await flushPromises();

        buttonWith(wrapper, "Install").at(0).vm.$emit("click");
        await flushPromises();

        // one request per repository rather than one silent request for all of them
        expect(vi.mocked(installWorkflowTools)).toHaveBeenCalledTimes(2);
        const names = vi.mocked(installWorkflowTools).mock.calls.map((call) => (call[1] as any)[0].name);
        expect(names).toEqual(["text_processing", "fastp"]);
    });

    it("installs a repository once even when several of its tools are missing", async () => {
        vi.mocked(getWorkflowToolAvailability).mockResolvedValue(
            // two tools of one repository, which is the usual shape of a text_processing workflow
            availability([
                shedTool("text_processing", "9.3+galaxy1", [], null, "tp_easyjoin_tool"),
                shedTool("text_processing", "9.3+galaxy1", [], null, "tp_tail_tool"),
            ]) as never,
        );
        const wrapper = mountDialog();
        await flushPromises();

        buttonWith(wrapper, "Install").at(0).vm.$emit("click");
        await flushPromises();
        expect(vi.mocked(installWorkflowTools)).toHaveBeenCalledTimes(1);
    });

    it("reports a repository that failed rather than counting it as installed", async () => {
        vi.mocked(getWorkflowToolAvailability).mockResolvedValue(
            availability([shedTool("text_processing", "9.3+galaxy1")]) as never,
        );
        vi.mocked(installWorkflowTools).mockResolvedValue({
            installed: [],
            failed: [
                {
                    repository: { tool_shed: "shed", owner: "bgruening", name: "text_processing" },
                    error: "Error cloning repository",
                },
            ],
        } as never);
        const wrapper = mountDialog();
        await flushPromises();

        buttonWith(wrapper, "Install").at(0).vm.$emit("click");
        await flushPromises();
        expect(wrapper.text()).toContain("Error cloning repository");
    });

    it("offers a non-admin the request instead of the install", async () => {
        vi.mocked(getWorkflowToolAvailability).mockResolvedValue(
            availability([shedTool("text_processing", "9.3+galaxy1")], false) as never,
        );
        vi.mocked(requestWorkflowToolInstallation).mockResolvedValue({
            notified_admins: ["admin@galaxy.demo"],
            shared: true,
            emailed: true,
        } as never);
        const wrapper = mountDialog();
        await flushPromises();

        expect(buttonWith(wrapper, "Install").length).toBe(0);
        expect(wrapper.text()).toContain("Only administrators can install tools.");

        buttonWith(wrapper, "Ask an administrator").at(0).vm.$emit("click");
        await flushPromises();
        expect(wrapper.text()).toContain("admin@galaxy.demo");
    });

    it("says so when nothing is missing", async () => {
        vi.mocked(getWorkflowToolAvailability).mockResolvedValue(availability([]) as never);
        const wrapper = mountDialog();
        await flushPromises();
        expect(wrapper.text()).toContain("Every tool this workflow uses is installed");
    });
});

import { getLocalVue, nth, suppressBootstrapVueWarnings, withPlugins } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import { isDate } from "date-fns";
import flushPromises from "flush-promises";
import { createPinia, disposePinia, setActivePinia } from "pinia";
import { afterEach, describe, expect, it, onTestFinished, vi } from "vitest";
import Multiselect from "vue-multiselect";

import type { WorkflowVersion } from "@/api/workflows";
import { useUserTagsStore } from "@/stores/userTagsStore";

import { UntypedParameters } from "./modules/parameters";

import WorkflowAttributes from "./WorkflowAttributes.vue";
import WorkflowVersionSelector from "@/components/Workflow/WorkflowVersionSelector.vue";

const TEST_ANNOTATION = "my cool annotation";
const TEST_NAME = "workflow_name";
const TEST_VERSIONS: WorkflowVersion[] = [
    { version: 0, update_time: "2022-01-02", steps: 10 },
    { version: 1, update_time: "2022-03-04", steps: 20 },
];
const autocompleteTags = ["#named_uer_tag", "abc", "my_tag"];

describe("WorkflowAttributes", () => {
    afterEach(() => {
        vi.clearAllTimers();
        vi.useRealTimers();
        vi.restoreAllMocks();
    });
    enableAutoUnmount(afterEach);

    it("renders attributes and updates the name and selected version", async () => {
        vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
        suppressBootstrapVueWarnings();

        const pinia = createPinia();
        onTestFinished(() => disposePinia(pinia));
        const localVue = getLocalVue(true);

        setActivePinia(pinia);

        const untypedParameters = new UntypedParameters();

        untypedParameters.getParameter("workflow_parameter_0");
        untypedParameters.getParameter("workflow_parameter_1");

        const wrapper = mount(WorkflowAttributes, {
            props: {
                id: "workflow_id",
                name: TEST_NAME,
                tags: ["workflow_tag_0", "workflow_tag_1"],
                parameters: untypedParameters,
                version: 0,
                versions: TEST_VERSIONS,
                annotation: TEST_ANNOTATION,
            },
            global: {
                ...withPlugins(localVue, pinia),
                stubs: { ...localVue.stubs, LicenseSelector: true },
            },
        });

        await flushPromises();

        const userTagsStore = useUserTagsStore(pinia);
        vi.spyOn(userTagsStore, "userTags", "get").mockReturnValue(autocompleteTags);
        userTagsStore.onNewTagSeen = vi.fn();
        userTagsStore.onTagUsed = vi.fn();
        userTagsStore.onMultipleNewTagsSeen = vi.fn();

        expect(wrapper.get(`[itemprop='description']`).attributes("content")).toBe(TEST_ANNOTATION);
        expect(wrapper.get(`[itemprop='name']`).attributes("content")).toBe(TEST_NAME);
        expect(wrapper.findComponent(WorkflowVersionSelector).exists()).toBeTruthy();

        const name = wrapper.get<HTMLInputElement>("#workflow-name");
        expect(name.element.value).toBe(TEST_NAME);
        await wrapper.setProps({ name: "new_workflow_name" });
        expect(name.element.value).toBe("new_workflow_name");

        const version = wrapper.getComponent(WorkflowVersionSelector);
        expect(version.props("version")).toBe(0);
        expect(version.props("versions")).toHaveLength(TEST_VERSIONS.length);
        expect(version.get("input.multiselect__input").attributes("aria-label")).toBe("Version");

        // When not on latest version, "switch to latest" link should be visible
        expect(wrapper.get("#workflow-version-area").text()).toContain("switch to latest");

        // When on latest version, should show "(latest version)" instead
        await wrapper.setProps({ version: 1 });
        expect(wrapper.get("#workflow-version-area").text()).toContain("latest version");
        expect(wrapper.get("#workflow-version-area").text()).not.toContain("switch to latest");

        // Check that version options have valid date labels
        const multiselect = version.getComponent(Multiselect);
        const options = multiselect.props("options") as { label: string; version: number }[];
        expect(options).toHaveLength(TEST_VERSIONS.length);
        for (const option of options) {
            const versionLabel = option.label;
            const versionDate = versionLabel.substring(versionLabel.indexOf(":") + 1, versionLabel.indexOf(",")).trim();
            expect(isDate(new Date(versionDate))).toBe(true);
        }

        const parameters = wrapper.findAll(".list-group-item");
        expect(parameters.length).toBe(2);
        expect(nth(parameters, 0).text()).toBe("1: workflow_parameter_0");
        expect(nth(parameters, 1).text()).toBe("2: workflow_parameter_1");
        expect(wrapper.get<HTMLTextAreaElement>("#workflow-annotation").element.value).toBe(TEST_ANNOTATION);
    });
});

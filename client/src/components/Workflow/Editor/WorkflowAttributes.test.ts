import { getLocalVue, suppressBootstrapVueWarnings } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { isDate } from "date-fns";
import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";
import { describe, expect, it, vi } from "vitest";
import Multiselect from "vue-multiselect";

import { useUserTagsStore } from "@/stores/userTagsStore";

import { UntypedParameters } from "./modules/parameters";

import WorkflowAttributes from "./WorkflowAttributes.vue";
import WorkflowVersionSelector from "@/components/Workflow/WorkflowVersionSelector.vue";

vi.mock("app", () => ({}));

const TEST_ANNOTATION = "my cool annotation";
const TEST_NAME = "workflow_name";
const TEST_VERSIONS = [
    { version: 0, update_time: "2022-01-02", steps: 10 },
    { version: 1, update_time: "2022-03-04", steps: 20 },
];
const autocompleteTags = ["#named_uer_tag", "abc", "my_tag"];

describe("WorkflowAttributes", () => {
    it("test attributes", async () => {
        suppressBootstrapVueWarnings();

        const pinia = createPinia();
        const localVue = getLocalVue(true);

        setActivePinia(pinia);

        const untypedParameters = new UntypedParameters();

        untypedParameters.getParameter("workflow_parameter_0");
        untypedParameters.getParameter("workflow_parameter_1");

        const wrapper = mount(WorkflowAttributes as object, {
            propsData: {
                id: "workflow_id",
                name: TEST_NAME,
                tags: ["workflow_tag_0", "workflow_tag_1"],
                parameters: untypedParameters,
                version: 0,
                versions: TEST_VERSIONS,
                annotation: TEST_ANNOTATION,
            },
            stubs: {
                LicenseSelector: true,
            },
            localVue,
            pinia,
        });

        await flushPromises();

        const userTagsStore = useUserTagsStore();
        vi.spyOn(userTagsStore, "userTags", "get").mockReturnValue(autocompleteTags);
        userTagsStore.onNewTagSeen = vi.fn();
        userTagsStore.onTagUsed = vi.fn();
        userTagsStore.onMultipleNewTagsSeen = vi.fn();

        expect(wrapper.find(`[itemprop='description']`).attributes("content")).toBe(TEST_ANNOTATION);
        expect(wrapper.find(`[itemprop='name']`).attributes("content")).toBe(TEST_NAME);
        expect(wrapper.findComponent(WorkflowVersionSelector).exists()).toBeTruthy();

        const name = wrapper.find("#workflow-name");
        expect((name.element as HTMLInputElement).value).toBe(TEST_NAME);
        await wrapper.setProps({ name: "new_workflow_name" });
        expect((name.element as HTMLInputElement).value).toBe("new_workflow_name");

        const version = wrapper.findComponent(WorkflowVersionSelector);
        expect(version.props("version")).toBe(0);
        expect(version.props("versions")).toHaveLength(TEST_VERSIONS.length);

        // Check that version options have valid date labels
        const multiselect = version.findComponent(Multiselect);
        const options = multiselect.props("options") as { label: string; version: number }[];
        expect(options).toHaveLength(TEST_VERSIONS.length);
        for (const option of options) {
            const versionLabel = option.label;
            const versionDate = versionLabel.substring(versionLabel.indexOf(":") + 1, versionLabel.indexOf(",")).trim();
            expect(isDate(new Date(versionDate))).toBe(true);
        }

        const parameters = wrapper.findAll(".list-group-item");
        expect(parameters.length).toBe(2);
        expect(parameters.at(0).text()).toBe("1: workflow_parameter_0");
        expect(parameters.at(1).text()).toBe("2: workflow_parameter_1");
        expect((wrapper.find("#workflow-annotation").element as HTMLInputElement).value).toBe(TEST_ANNOTATION);
    });
});

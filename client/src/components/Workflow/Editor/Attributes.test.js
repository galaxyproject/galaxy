import { createLocalVue, mount } from "@vue/test-utils";
import { isDate } from "date-fns";
import { computed } from "vue";

import { useUserTagsStore } from "@/stores/userTagsStore";

import Attributes from "./Attributes";
import { UntypedParameters } from "./modules/parameters";

jest.mock("app");

const TEST_ANNOTATION = "my cool annotation";
const TEST_NAME = "workflow_name";
const TEST_VERSIONS = [
    { version: 0, update_time: "2022-01-02", steps: 10 },
    { version: 1, update_time: "2022-03-04", steps: 20 },
];
const autocompleteTags = ["#named_uer_tag", "abc", "my_tag"];

jest.mock("@/stores/userTagsStore");
useUserTagsStore.mockReturnValue({
    userTags: computed(() => autocompleteTags),
    onNewTagSeen: jest.fn(),
    onTagUsed: jest.fn(),
    onMultipleNewTagsSeen: jest.fn(),
});

describe("Attributes", () => {
    it("test attributes", async () => {
        const localVue = createLocalVue();
        const untypedParameters = new UntypedParameters();
        untypedParameters.getParameter("workflow_parameter_0");
        untypedParameters.getParameter("workflow_parameter_1");
        const wrapper = mount(Attributes, {
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
        });
        expect(wrapper.find(`[itemprop='description']`).attributes("content")).toBe(TEST_ANNOTATION);
        expect(wrapper.find(`[itemprop='name']`).attributes("content")).toBe(TEST_NAME);
        expect(wrapper.find(`#workflow-version-area > select`).exists()).toBeTruthy();

        const name = wrapper.find("#workflow-name");
        expect(name.element.value).toBe(TEST_NAME);
        await wrapper.setProps({ name: "new_workflow_name" });
        expect(name.element.value).toBe("new_workflow_name");

        const version = wrapper.findAllComponents(`#workflow-version-area > select > option`);
        expect(version).toHaveLength(TEST_VERSIONS.length);
        for (let i = 0; i < version.length; i++) {
            const versionLabel = version.at(i).text();
            const versionDate = versionLabel.substring(versionLabel.indexOf(":") + 1, versionLabel.indexOf(",")).trim();
            expect(isDate(new Date(versionDate))).toBe(true);
        }

        const parameters = wrapper.findAll(".list-group-item");
        expect(parameters.length).toBe(2);
        expect(parameters.at(0).text()).toBe("1: workflow_parameter_0");
        expect(parameters.at(1).text()).toBe("2: workflow_parameter_1");
        expect(wrapper.find("#workflow-annotation").element.value).toBe(TEST_ANNOTATION);
    });
});

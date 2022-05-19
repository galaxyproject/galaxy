import { mount, createLocalVue } from "@vue/test-utils";
import Attributes from "./Attributes";
import { UntypedParameters } from "./modules/parameters";
import { isDate } from "date-fns";

jest.mock("app");

const TEST_ANNOTATION = "my cool annotation";
const TEST_NAME = "workflow_name";
const TEST_VERSIONS = [  //TODO (high) does it make sense to pre-fill this, if this is coming from prior user actions?
    { versions: 0, update_time: "2022-01-01", steps: 10 },
    { versions: 1, update_time: "2022-01-02", steps: 20 },
];

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
        expect(wrapper.find(`#workflow-version-area`).attributes("value")); //TODO (low) does an `itemprop` need to be created in Attributes.vue (and why)?

        const name = wrapper.find("#workflow-name");
        expect(name.element.value).toBe(TEST_NAME);
        await wrapper.setProps({ name: "new_workflow_name" });
        expect(name.element.value).toBe("new_workflow_name");

        const versionArea = wrapper.find("#workflow-version-area").attributes("value"); //TODO (high) does `wrapper` = document.getElementById("workflow-version-area");
        var version = versionArea.querySelector("select[class='custom-select']");        
        for (const v of version) {
            const versionDate = (v.label).substring(versionLabel.indexOf(":") + 1, (v.label).indexOf(",")).trim();
            expect(isDate(new Date(versionDate))).toBe(true);
        }

        const parameters = wrapper.findAll(".list-group-item"); //TODO (nit) not part of my fix, just curious: is this supposed to this exist in the code?
        expect(parameters.length).toBe(2);
        expect(parameters.at(0).text()).toBe("1: workflow_parameter_0");
        expect(parameters.at(1).text()).toBe("2: workflow_parameter_1");
        console.log(wrapper.html()); //TODO (low) we don't need this, right?
        expect(wrapper.find("#workflow-annotation").element.value).toBe(TEST_ANNOTATION);
    });
});

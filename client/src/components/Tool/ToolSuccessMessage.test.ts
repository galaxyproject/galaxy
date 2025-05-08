import { mount, type Wrapper } from "@vue/test-utils";

import jobInformationResponse from "@/components/JobInformation/testData/jobInformationResponse.json";

import ToolSuccessMessage from "./ToolSuccessMessage.vue";

// Prop constants
const TEST_JOB_RESPONSE = {
    produces_entry_points: false,
    jobs: [jobInformationResponse],
    outputs: [
        {
            hid: 0,
            name: "output1",
        },
    ],
    output_collections: [
        {
            hid: 1,
            name: "collection1",
        },
    ],
};
const TEST_TOOL_NAME = "Test Tool";

// Selectors
const SELECTORS = {
    SINGULAR_JOB_LINK: "[data-description='singular job link']",
    JOB_LINK: "[data-description='job link']",
    OUTPUTS_LIST: "[data-description='list of outputs']",
};

describe("ToolSuccessMessage", () => {
    let wrapper: Wrapper<Vue>;

    beforeEach(async () => {
        wrapper = mount(ToolSuccessMessage as object, {
            propsData: {
                jobResponse: TEST_JOB_RESPONSE,
                toolName: TEST_TOOL_NAME,
            },
            stubs: {
                FontAwesomeIcon: true,
            },
        });
    });

    it("shows both dataset and collection outputs correctly", async () => {
        expect(wrapper.find(SELECTORS.OUTPUTS_LIST).text()).toContain(
            `${TEST_JOB_RESPONSE.outputs[0]?.hid}: ${TEST_JOB_RESPONSE.outputs[0]?.name}`
        );
        expect(wrapper.find(SELECTORS.OUTPUTS_LIST).text()).toContain(
            `${TEST_JOB_RESPONSE.output_collections[0]?.hid}: ${TEST_JOB_RESPONSE.output_collections[0]?.name}`
        );
    });

    it("has a link to the singular job", () => {
        expect(wrapper.find(SELECTORS.SINGULAR_JOB_LINK).exists()).toBe(true);
    });

    it("shows the tool name", () => {
        expect(wrapper.text()).toContain(`Started tool ${TEST_TOOL_NAME}`);
    });

    it("has a link to each job when multiple jobs are present", async () => {
        await wrapper.setProps({
            jobResponse: {
                ...TEST_JOB_RESPONSE,
                jobs: [
                    jobInformationResponse,
                    {
                        ...jobInformationResponse,
                        id: "test_id_2",
                    },
                ],
            },
        });
        expect(wrapper.findAll(SELECTORS.JOB_LINK).length).toBe(2);
    });
});

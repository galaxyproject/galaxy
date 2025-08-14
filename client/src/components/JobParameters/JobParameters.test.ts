import { mount, type VueWrapper } from "@vue/test-utils";
import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import flushPromises from "flush-promises";
import { createPinia } from "pinia";

import raw from "@/components/providers/test/json/Dataset.json";

import paramResponse from "./parameters-response.json";

import JobParameters from "./JobParameters.vue";

const JOB_ID = "foo";
const DatasetProvider: any = {
    render() {
        return this.$slots.default({
            loading: false,
            result: raw,
        });
    },
};
const pinia = createPinia();

describe("JobParameters/JobParameters.vue", () => {
    const linkParam = paramResponse.parameters.find((element) => Array.isArray(element.value)) ?? {
        text: "Test Parameter not found",
        value: "NOT FOUND",
    };
    let axiosMock: MockAdapter;

    beforeEach(() => {
        axiosMock = new MockAdapter(axios);
        axiosMock.onGet(`/api/jobs/${JOB_ID}/parameters_display`).reply(200, paramResponse);
    });

    afterEach(() => {
        axiosMock.restore();
    });

    it("should render job parameters", async () => {
        const props = {
            jobId: JOB_ID,
        };

        const wrapper = mount(JobParameters as object, {
            props,
            stubs: {
                DatasetProvider: DatasetProvider,
                ContentItem: true,
            },
            pinia,
        });
        await flushPromises();

        const checkTableParameter = (
            element: any,
            expectedTitle: string,
            expectedValue: string | { hid: number; name: string },
            link?: string,
        ) => {
            const tds = element.findAll("td");
            expect(tds[0]!.text()).toBe(expectedTitle);
            if (typeof expectedValue === "string") {
                expect(tds[1]!.text()).toContain(expectedValue);
            } else {
                const contentItem = tds[1].find("contentitem-stub");
                expect(contentItem.attributes("id")).toBe(`${expectedValue.hid}`);
                expect(contentItem.attributes("name")).toBe(expectedValue.name);
            }
            if (link) {
                const a_element = tds[1].find("a");
                expect(a_element.attributes("href")).toBe(link);
            }
        };
        // parameter table
        const tbody = wrapper.find("#tool-parameters > tbody");
        expect(tbody.exists()).toBe(true);

        // table elements
        const elements = tbody.findAll("tr");
        expect(elements.length).toBe(3);

        checkTableParameter(elements[0], "Add this value", "22", undefined);
        checkTableParameter(elements[1], linkParam.text, { hid: raw.hid, name: raw.name }, undefined);
        checkTableParameter(elements[2], "Iterate?", "NO", undefined);
    });

    it("should show only single parameter", async () => {
        const props = {
            jobId: JOB_ID,
            param: "Iterate?",
        };

        const getSingleParam = async (props: { jobId: string; param: string }) => {
            const wrapper = mount(JobParameters as object, {
                props,
                stubs: {
                    DatasetProvider: DatasetProvider,
                    ContentItem: true,
                },
                pinia,
            });
            await flushPromises();
            return wrapper.find("#single-param");
        };

        const singleParam = await getSingleParam(props);

        expect(singleParam.text()).toBe("NO");
    });
});

import { mount, type Wrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";

import paramResponse from "./parameters-response.json";

import JobParameters from "./JobParameters.vue";

const JOB_ID = "foo";
const pinia = createPinia();
const { server, http } = useServerMock();

describe("JobParameters/JobParameters.vue", () => {
    const linkParam = paramResponse.parameters.find((element) => Array.isArray(element.value)) ?? {
        text: "Test Parameter not found",
        value: "NOT FOUND",
    };

    beforeEach(() => {
        server.use(
            http.untyped.get(`/api/jobs/${JOB_ID}/parameters_display`, () => {
                return HttpResponse.json(paramResponse);
            }),
        );
    });

    it("should render job parameters", async () => {
        const propsData = {
            jobId: JOB_ID,
        };

        const wrapper = mount(JobParameters as object, {
            propsData,
            stubs: {
                GenericHistoryItem: true,
            },
            pinia,
        });
        await flushPromises();

        const checkTableParameter = (
            element: Wrapper<any>,
            expectedTitle: string,
            expectedValue: string | { id: string; src: string },
            link?: string,
        ) => {
            const tds = element.findAll("td");
            expect(tds.at(0).text()).toBe(expectedTitle);
            if (typeof expectedValue === "string") {
                expect(tds.at(1).text()).toContain(expectedValue);
            } else {
                const genericItem = tds.at(1).find("generichistoryitem-stub");
                expect(genericItem.attributes("item-id")).toBe(expectedValue.id);
                expect(genericItem.attributes("item-src")).toBe(expectedValue.src);
            }
            if (link) {
                const a_element = tds.at(1).find("a");
                expect(a_element.attributes("href")).toBe(link);
            }
        };
        // parameter table
        const tbody = wrapper.find("#tool-parameters > tbody");
        expect(tbody.exists()).toBe(true);

        // table elements
        const elements = tbody.findAll("tr");
        expect(elements.length).toBe(3);

        checkTableParameter(elements.at(0), "Add this value", "22", undefined);
        const firstVal = Array.isArray(linkParam.value) ? linkParam.value[0] : { id: "", src: "" };
        checkTableParameter(
            elements.at(1),
            linkParam.text,
            { id: firstVal?.id || "", src: firstVal?.src || "" },
            undefined,
        );
        checkTableParameter(elements.at(2), "Iterate?", "NO", undefined);
    });

    it("should show only single parameter", async () => {
        const propsData = {
            jobId: JOB_ID,
            param: "Iterate?",
        };

        const getSingleParam = async (_props: { jobId: string; param: string }) => {
            const wrapper = mount(JobParameters as object, {
                props: propsData,
                stubs: {
                    GenericHistoryItem: true,
                },
                pinia,
            });
            await flushPromises();
            return wrapper.find("#single-param");
        };

        const singleParam = await getSingleParam(propsData);

        expect(singleParam.text()).toBe("NO");
    });
});

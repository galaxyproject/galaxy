import { getFakeRegisteredUser } from "@tests/test-data";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { enableAutoUnmount, shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia } from "pinia";
import { afterEach, describe, expect, it } from "vitest";

import type { RegisteredUser } from "@/api";
import { useServerMock } from "@/api/client/__mocks__";
import type { JobDestinationParams as JobDestinationParameters } from "@/api/jobs";
import { useUserStore } from "@/stores/userStore";

import jobDestinationResponseData from "./testData/jobDestinationResponse.json";

import JobDestinationParams from "./JobDestinationParams.vue";

const JOB_ID = "foo_job_id";

const localVue = getLocalVue();

const jobDestinationResponse = jobDestinationResponseData satisfies JobDestinationParameters;

const { server, http } = useServerMock();

enableAutoUnmount(afterEach);

async function mountJobDestinationParams(user: RegisteredUser | null) {
    server.use(
        http.get("/api/jobs/{job_id}/destination_params", ({ response }) => {
            return response(200).json(jobDestinationResponse);
        }),
    );

    const pinia = createPinia();
    useUserStore(pinia).currentUser = user;

    const wrapper = shallowMount(JobDestinationParams, {
        props: {
            jobId: JOB_ID,
        },
        global: withPlugins(localVue, pinia),
    });

    await flushPromises();

    return wrapper;
}

describe("JobDestinationParams", () => {
    it("renders every destination parameter for an admin, with null values left blank", async () => {
        const wrapper = await mountJobDestinationParams(getFakeRegisteredUser({ is_admin: true }));

        const rows = wrapper.get("#destination_parameters").findAll("tbody > tr");
        const renderedParameters = rows.map((row) => row.findAll("td").map((cell) => cell.text()));
        const expectedParameters = Object.entries(jobDestinationResponse).map(([title, value]) => [title, value ?? ""]);

        expect(expectedParameters.length).toBeGreaterThan(0);
        expect(renderedParameters).toEqual(expectedParameters);
    });

    it.each([
        ["a registered non-admin", getFakeRegisteredUser()],
        ["a visitor without a loaded user", null],
    ])("hides destination parameters from %s", async (_description, user) => {
        const wrapper = await mountJobDestinationParams(user);

        expect(wrapper.find("#destination_parameters").exists()).toBe(false);
        expect(wrapper.find("#destination-parameters-heading").exists()).toBe(false);
    });
});

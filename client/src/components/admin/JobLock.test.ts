import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { describe, expect, it } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";

import JobLock from "./JobLock.vue";

const { server, http } = useServerMock();

const globalConfig = getLocalVue();

describe("JobLock", () => {
    it("locks job dispatching from the switch", async () => {
        const requests: unknown[] = [];
        server.use(
            http.get("/api/job_lock", ({ response }) => response(200).json({ active: false })),
            http.put("/api/job_lock", async ({ request, response }) => {
                const body = (await request.json()) as { active: boolean };
                requests.push(body);
                return response(200).json(body);
            }),
        );
        const wrapper = mount(JobLock as object, { global: globalConfig });
        await flushPromises();
        requests.length = 0;

        const input = wrapper.find("#prevent-job-dispatching");
        expect(input.attributes("role")).toBe("switch");
        expect(wrapper.find('[data-test-id="prevent-job-dispatching-label"] strong').text()).toBe("unlocked");

        await input.setValue(true);
        await flushPromises();

        expect(requests).toEqual([{ active: true }]);
        expect(wrapper.find('[data-test-id="prevent-job-dispatching-label"] strong').text()).toBe("locked");
    });
});

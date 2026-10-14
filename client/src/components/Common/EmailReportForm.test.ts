import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { describe, expect, it, vi } from "vitest";

import { sanitizeHtml } from "@/directives/sanitizeHtml";

import EmailReportForm from "./EmailReportForm.vue";

describe("EmailReportForm", () => {
    it("renders report results through v-sanitize-html with the links profile", async () => {
        vi.mocked(sanitizeHtml).mockClear();
        const submit = vi.fn(async () => [["Created [issue #1](https://github.com/org/repo/issues/1)", "success"]]);
        const wrapper = mount(EmailReportForm as object, {
            localVue: getLocalVue(),
            pinia: createTestingPinia({ createSpy: vi.fn }),
            propsData: { submit },
        });

        await wrapper.find("#email-report-submit").trigger("click");
        await flushPromises();

        const call = vi.mocked(sanitizeHtml).mock.calls.find(([html]) => html?.includes("issue #1"));
        expect(call?.[1]).toBe("links");
        expect(call?.[0]).toContain('href="https://github.com/org/repo/issues/1" target="_blank"');
        expect(wrapper.find(".alert a").text()).toBe("issue #1");
    });
});

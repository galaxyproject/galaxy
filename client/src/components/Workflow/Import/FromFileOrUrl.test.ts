import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import FromFile from "./FromFile.vue";
import FromUrl from "./FromUrl.vue";

let lastPostRequest: Map<string, string>;

vi.mock("axios", () => ({
    default: {
        post: vi.fn((_url, request) => {
            lastPostRequest = request;
        }),
        isAxiosError: vi.fn(() => true),
    },
}));

const localVue = getLocalVue(true);

const sharedUrl = "http://127.0.0.1:8081/u/admin/w/unnamed-workflow";
const sharedUrlTrailingSlash = "http://127.0.0.1:8081/u/admin/w/unnamed-workflow/";
const sharedUrlJson = "http://127.0.0.1:8081/u/admin/w/unnamed-workflow/json";
const invalidUrl = "http://127.0.0.1:8081/u/admin/w/unnamed-workflow/additional-stuff/";

describe("FromUrl", () => {
    it("converts shared urls to json urls", async () => {
        const wrapper = mount(FromUrl as object, { localVue });

        {
            const input = wrapper.find("#workflow-import-url-input");
            await input.setValue(sharedUrl);

            const form = wrapper.find("form");
            await form.trigger("submit");

            expect(lastPostRequest.get("archive_source")).toEqual(sharedUrlJson);
        }

        {
            const input = wrapper.find("#workflow-import-url-input");
            await input.setValue(sharedUrlTrailingSlash);

            const form = wrapper.find("form");
            await form.trigger("submit");

            expect(lastPostRequest.get("archive_source")).toEqual(sharedUrlJson);
        }

        {
            const input = wrapper.find("#workflow-import-url-input");
            await input.setValue(sharedUrlJson);

            const form = wrapper.find("form");
            await form.trigger("submit");

            expect(lastPostRequest.get("archive_source")).toEqual(sharedUrlJson);
        }

        {
            const input = wrapper.find("#workflow-import-url-input");
            await input.setValue(invalidUrl);

            const form = wrapper.find("form");
            await form.trigger("submit");

            expect(lastPostRequest.get("archive_source")).toEqual(invalidUrl);
        }
    });
});

describe("FromFile", () => {
    it("can mount the component", async () => {
        const wrapper = mount(FromFile as object, { localVue });
        expect(wrapper.find("#workflow-import-button").exists()).toBe(true);
    });
});

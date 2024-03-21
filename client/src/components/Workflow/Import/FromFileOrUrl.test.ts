import { getLocalVue } from "@tests/jest/helpers";
import { mount } from "@vue/test-utils";

import FromFileOrUrl from "./FromFileOrUrl.vue";

let lastPostRequest: Map<string, string>;

jest.mock("axios", () => ({
    post: jest.fn((_url, request) => {
        lastPostRequest = request;
    }),
}));

const localVue = getLocalVue(true);

const sharedUrl = "http://127.0.0.1:8081/u/admin/w/unnamed-workflow";
const sharedUrlTrailingSlash = "http://127.0.0.1:8081/u/admin/w/unnamed-workflow/";
const sharedUrlJson = "http://127.0.0.1:8081/u/admin/w/unnamed-workflow/json";
const invalidUrl = "http://127.0.0.1:8081/u/admin/w/unnamed-workflow/additional-stuff/";

describe("FromFileOrUrl", () => {
    it("converts shared urls to json urls", async () => {
        const wrapper = mount(FromFileOrUrl, { localVue });

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

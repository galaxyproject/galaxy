import { getLocalVue } from "@tests/vitest/helpers";
import { setupMockConfig } from "@tests/vitest/mockConfig";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";

import StsDownloadButton from "./StsDownloadButton.vue";

const localVue = getLocalVue();
const { server, http } = useServerMock();

const NO_TASKS_CONFIG = {
    enable_celery_tasks: false,
};
const TASKS_CONFIG = {
    enable_celery_tasks: true,
};
const FALLBACK_URL = "http://cow.com/direct_download";
const DOWNLOAD_ENDPOINT = "http://cow.com/prepare_download";
const STORAGE_REQUEST_ID = "moocow1235";
const POLL_DELAY = 200;

async function mountStsDownloadButtonWrapper(config) {
    setupMockConfig(config);

    const pinia = createPinia();
    const wrapper = mount(StsDownloadButton, {
        props: {
            title: "my title",
            fallbackUrl: FALLBACK_URL,
            downloadEndpoint: DOWNLOAD_ENDPOINT,
        },
        global: localVue,
        pinia,
    });
    await flushPromises();
    return wrapper;
}

describe("StsDownloadButton", () => {
    beforeEach(async () => {
        // Reset handlers before each test
    });

    it("should fallback to a URL if tasks not enabled", async () => {
        const windowSpy = vi.spyOn(window, "open");
        windowSpy.mockImplementation(() => {});
        const wrapper = await mountStsDownloadButtonWrapper(NO_TASKS_CONFIG);
        await wrapper.find("button").trigger("click");
        await flushPromises();
        expect(window.open).toHaveBeenCalled();
    });

    it("should poll until ready", async () => {
        server.use(
            http.untyped.post(DOWNLOAD_ENDPOINT, () => {
                return HttpResponse.json({ storage_request_id: STORAGE_REQUEST_ID });
            }),
            http.untyped.get(`api/short_term_storage/${STORAGE_REQUEST_ID}/ready`, () => {
                return HttpResponse.json(true);
            }),
        );
        const wrapper = await mountStsDownloadButtonWrapper(TASKS_CONFIG);

        await wrapper.find("button").trigger("click");
        await flushPromises();
        expect(window.location).toBeAt(`api/short_term_storage/${STORAGE_REQUEST_ID}`);
    });

    it("should be in a waiting state while polling", async () => {
        server.use(
            http.untyped.post(DOWNLOAD_ENDPOINT, () => {
                return HttpResponse.json({ storage_request_id: STORAGE_REQUEST_ID });
            }),
            http.untyped.get(`api/short_term_storage/${STORAGE_REQUEST_ID}/ready`, () => {
                return HttpResponse.json(false);
            }),
        );
        const wrapper = await mountStsDownloadButtonWrapper(TASKS_CONFIG);

        expect(wrapper.find(".fa-spinner").exists()).toBeFalsy();
        await wrapper.find("button").trigger("click");
        await flushPromises();
        expect(wrapper.find(".fa-spinner").exists()).toBeTruthy();
    });

    it.each([
        ["ready", true],
        ["not ready", false],
    ])("should not poll or navigate when a %s response arrives after unmount", async (_label, ready) => {
        const storageRequestId = `in-flight-poll-${ready}`;
        let readyRequests = 0;
        let releasePendingPoll;
        const pendingPoll = new Promise((resolve) => (releasePendingPoll = resolve));
        server.use(
            http.untyped.post(DOWNLOAD_ENDPOINT, () => {
                return HttpResponse.json({ storage_request_id: storageRequestId });
            }),
            http.untyped.get(`api/short_term_storage/${storageRequestId}/ready`, async () => {
                readyRequests += 1;
                if (readyRequests > 1) {
                    await pendingPoll;
                    return HttpResponse.json(ready);
                }
                return HttpResponse.json(false);
            }),
        );
        const wrapper = await mountStsDownloadButtonWrapper(TASKS_CONFIG);
        const assignSpy = vi.spyOn(window.location, "assign");
        vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
        try {
            await wrapper.find("button").trigger("click");
            await flushPromises();
            expect(readyRequests).toBe(1);

            vi.advanceTimersByTime(POLL_DELAY);
            await vi.waitFor(() => expect(readyRequests).toBe(2));

            wrapper.unmount();
            releasePendingPoll();
            await flushPromises();
            vi.advanceTimersByTime(POLL_DELAY * 10);
            await flushPromises();
            expect(readyRequests).toBe(2);
            expect(assignSpy).not.toHaveBeenCalled();
        } finally {
            vi.useRealTimers();
        }
    });

    it("should not start polling when the prepare request resolves after unmount", async () => {
        const storageRequestId = "in-flight-prepare";
        let readyRequests = 0;
        let releasePendingPost;
        const pendingPost = new Promise((resolve) => (releasePendingPost = resolve));
        server.use(
            http.untyped.post(DOWNLOAD_ENDPOINT, async () => {
                await pendingPost;
                return HttpResponse.json({ storage_request_id: storageRequestId });
            }),
            http.untyped.get(`api/short_term_storage/${storageRequestId}/ready`, () => {
                readyRequests += 1;
                return HttpResponse.json(false);
            }),
        );
        const wrapper = await mountStsDownloadButtonWrapper(TASKS_CONFIG);

        await wrapper.find("button").trigger("click");
        wrapper.unmount();
        releasePendingPost();
        await flushPromises();
        await new Promise((resolve) => setTimeout(resolve, POLL_DELAY * 2));
        expect(readyRequests).toBe(0);
    });
});

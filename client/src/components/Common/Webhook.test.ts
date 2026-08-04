import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";

import Webhook from "./Webhook.vue";

const { WEBHOOK, targetExistsAtInjection } = vi.hoisted(() => ({
    WEBHOOK: { id: "phdcomics", type: ["tool"], weight: 1, script: "/* noop */", styles: "" },
    // Records whether the target mount point existed in the document at the
    // moment the webhook script would have been injected.
    targetExistsAtInjection: vi.fn(),
}));

vi.mock("@/utils/webhooks", () => ({
    loadWebhooks: vi.fn().mockResolvedValue([WEBHOOK]),
    pickWebhook: vi.fn().mockReturnValue(WEBHOOK),
}));

vi.mock("@/utils/utils", () => ({
    appendScriptStyle: (data: { id?: string }) => {
        targetExistsAtInjection(Boolean(data.id && document.getElementById(data.id)));
    },
}));

const localVue = getLocalVue();

describe("Webhook.vue", () => {
    beforeEach(() => {
        targetExistsAtInjection.mockClear();
    });

    it("renders the webhook mount point before injecting its script", async () => {
        mount(Webhook as object, {
            localVue,
            propsData: { type: "tool", toolId: "cat1", toolVersion: "1.0" },
            attachTo: document.body,
        });

        await flushPromises();

        expect(targetExistsAtInjection).toHaveBeenCalledTimes(1);
        // Injected script queries `#<webhookId>`; that div must exist when it runs.
        expect(targetExistsAtInjection).toHaveBeenCalledWith(true);
    });
});

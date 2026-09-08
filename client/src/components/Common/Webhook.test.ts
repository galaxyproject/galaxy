import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";

import Webhook from "./Webhook.vue";

interface WebhookData {
    id: string;
    type: string[];
    weight: number;
    activate: boolean;
    script: string;
    styles: string;
}

const { fixtures, loadWebhooks, pickWebhook, appendScriptStyle, targetExistsAtInjection } = vi.hoisted(() => {
    const activeTool = {
        id: "phdcomics",
        type: ["tool"],
        weight: 1,
        activate: true,
        script: "/* noop */",
        styles: "",
    };
    const inactiveTool = {
        id: "inactive_tool_webhook",
        type: ["tool"],
        weight: 1,
        activate: false,
        script: "/* noop */",
        styles: "",
    };
    const activeMasthead = {
        id: "searchover",
        type: ["masthead"],
        weight: 1,
        activate: true,
        script: "/* uses Backbone */",
        styles: "",
    };
    const all = [activeTool, inactiveTool, activeMasthead];

    // Records whether the target mount point existed in the document at the
    // moment the webhook script would have been injected.
    const targetExistsAtInjection = vi.fn();

    return {
        fixtures: { activeTool, inactiveTool, activeMasthead, all },
        // Mirrors the real `loadWebhooks` type filter: everything when no type is given.
        loadWebhooks: vi.fn(async (type?: string) =>
            type ? all.filter((webhook) => webhook.type.includes(type)) : all,
        ),
        pickWebhook: vi.fn((webhooks: WebhookData[]) => webhooks[0]),
        appendScriptStyle: vi.fn((data: { id?: string }) => {
            targetExistsAtInjection(Boolean(data.id && document.getElementById(data.id)));
        }),
        targetExistsAtInjection,
    };
});

vi.mock("@/utils/webhooks", () => ({
    loadWebhooks,
    pickWebhook,
}));

vi.mock("@/utils/utils", () => ({
    appendScriptStyle,
}));

const localVue = getLocalVue();

describe("Webhook.vue", () => {
    beforeEach(() => {
        vi.clearAllMocks();
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

    it("only considers active webhooks matching its type", async () => {
        mount(Webhook as object, {
            localVue,
            propsData: { type: "tool", toolId: "cat1", toolVersion: "1.0" },
            attachTo: document.body,
        });

        await flushPromises();

        expect(loadWebhooks).toHaveBeenCalledWith("tool");

        expect(pickWebhook).toHaveBeenCalledTimes(1);
        const candidates = pickWebhook.mock.calls[0]?.[0];
        expect(candidates).toEqual([fixtures.activeTool]);
        expect(candidates).not.toContain(fixtures.inactiveTool);
        expect(candidates).not.toContain(fixtures.activeMasthead);

        expect(appendScriptStyle).toHaveBeenCalledTimes(1);
        expect(appendScriptStyle).toHaveBeenCalledWith(fixtures.activeTool);
    });
});

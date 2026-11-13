import { getLocalVue } from "@tests/vitest/helpers";
import { DOMWrapper, mount, type VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { HttpResponse } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import type { UserNotificationPreferences } from "@/api/notifications";
import { setMockConfig } from "@/composables/__mocks__/config";

import CompletionNotification from "@/components/Notifications/CompletionNotification.vue";

vi.mock("@/composables/config");

const { server, http } = useServerMock();
const category = "workflow_execution_completed";
const bellSelector = "[data-test-id='completion-notification-button']";
const notificationSelector = "[data-test-id='send-notification-checkbox']";
const emailSelector = "[data-test-id='completion-email-checkbox']";
const body = new DOMWrapper(document.body);
let preferences: UserNotificationPreferences;
let updates: unknown[];
let reads: number;
let wrappers: VueWrapper[];

async function mountControl(kind: "workflow" | "tool" = "workflow", open = true) {
    const wrapper = mount(CompletionNotification, {
        attachTo: document.body,
        props: {
            kind,
            value: false,
            onInput: (value: boolean) => Promise.resolve().then(() => wrapper.setProps({ value })),
        },
        global: getLocalVue(),
    });
    wrappers.push(wrapper);
    await flushPromises();
    if (open) {
        await wrapper.get(bellSelector).trigger("click");
    }
    await flushPromises();
    return wrapper;
}

describe("Run completion notification bell", () => {
    beforeEach(() => {
        setMockConfig({ enable_notification_system: true });
        updates = [];
        reads = 0;
        wrappers = [];
        preferences = {
            [category]: { enabled: true, channels: { email: false, push: true } },
            tool_execution_completed: { enabled: true, channels: { email: false, push: true } },
            message: { enabled: true, channels: { email: true, push: true } },
        };
        server.use(
            http.get("/api/notifications/preferences", ({ response }) => {
                reads++;
                return response(200).json({ preferences }, { headers: { "supported-channels": "push,email" } });
            }),
            http.put("/api/notifications/preferences", async ({ request, response }) => {
                const payload = await request.json();
                updates.push(payload);
                preferences = { ...preferences, ...payload.preferences };
                return response(200).json({ preferences });
            }),
        );
    });

    afterEach(() => {
        wrappers.forEach((wrapper) => wrapper.unmount());
        document.body.innerHTML = "";
    });

    it("starts off and loads delivery preferences only when the bell is opened", async () => {
        const wrapper = await mountControl("tool", false);
        expect(reads).toBe(0);
        expect(wrapper.get(bellSelector).attributes("aria-label")).toContain("off for this run");
        await wrapper.get(bellSelector).trigger("click");
        await flushPromises();
        expect(reads).toBe(1);
        expect(body.get<HTMLInputElement>(notificationSelector).element.checked).toBe(false);
    });

    it.each(["tool", "workflow"] as const)("keeps the %s notification choice local to this run", async (kind) => {
        const wrapper = await mountControl(kind);
        await body.get(notificationSelector).setValue(true);
        await flushPromises();
        expect(wrapper.props("value")).toBe(true);
        expect(wrapper.get(bellSelector).attributes("aria-label")).toContain("on for this run");
        await body.get(notificationSelector).setValue(false);
        await flushPromises();
        expect(updates).toEqual([]);
        expect(preferences[category]!.enabled).toBe(true);
    });

    it.each(["tool", "workflow"] as const)(
        "saves only %s delivery settings without opting this run in",
        async (kind) => {
            const key = kind === "tool" ? "tool_execution_completed" : category;
            const wrapper = await mountControl(kind);
            await body.get(emailSelector).setValue(true);
            await flushPromises();
            expect(updates).toEqual([
                { preferences: { [key]: { enabled: true, channels: { email: true, push: true } } } },
            ]);
            expect(preferences.message!.channels.email).toBe(true);
            expect(wrapper.props("value")).toBe(false);
            expect(body.text()).toContain("Saved for future and active");
        },
    );

    it("warns about an account mute and does not silently undo it when changing email", async () => {
        preferences[category]!.enabled = false;
        await mountControl();
        expect(body.text()).toContain("notifications are off in your account");
        await body.get(emailSelector).setValue(true);
        await flushPromises();
        expect(preferences[category]!.enabled).toBe(false);
    });

    it("keeps the saved email setting when an update fails and releases the run button", async () => {
        const wrapper = await mountControl();
        server.use(http.put("/api/notifications/preferences", () => HttpResponse.error()));
        await body.get(emailSelector).setValue(true);
        await flushPromises();
        expect(body.get<HTMLInputElement>(emailSelector).element.checked).toBe(false);
        expect(body.text()).toContain("Could not load or save settings");
        expect(wrapper.emitted("busy")?.at(-1)).toEqual([false]);
    });

    it("allows a per-run request even if delivery preferences cannot be loaded", async () => {
        server.use(http.get("/api/notifications/preferences", () => HttpResponse.error()));
        const wrapper = await mountControl();
        expect(body.text()).toContain("Retry");
        await body.get(notificationSelector).setValue(true);
        await flushPromises();
        expect(wrapper.props("value")).toBe(true);
        expect(updates).toEqual([]);
    });

    it("explains when email is unavailable", async () => {
        server.use(
            http.get("/api/notifications/preferences", ({ response }) =>
                response(200).json({ preferences }, { headers: { "supported-channels": "push" } }),
            ),
        );
        await mountControl();
        expect(body.find(emailSelector).exists()).toBe(false);
        expect(body.text()).toContain("Email delivery is not available");
    });

    it("hides the bell when notifications are disabled", async () => {
        setMockConfig({ enable_notification_system: false });
        const wrapper = await mountControl("workflow", false);
        expect(wrapper.find(bellSelector).exists()).toBe(false);
        expect(reads).toBe(0);
    });
});

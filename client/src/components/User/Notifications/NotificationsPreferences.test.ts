import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia } from "pinia";
import { describe, expect, it } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";

import NotificationsPreferences from "./NotificationsPreferences.vue";

const localVue = getLocalVue();

const { server, http } = useServerMock();

const channels = { email: true, push: true };

describe("NotificationsPreferences", () => {
    it("shows the preferences when it is mounted before the configuration has loaded", async () => {
        server.use(
            http.get("/api/configuration", ({ response }) => {
                return response.untyped(HttpResponse.json({ enable_notification_system: true }));
            }),
            http.get("/api/notifications/preferences", ({ response }) => {
                return response.untyped(
                    HttpResponse.json(
                        {
                            preferences: {
                                message: { enabled: true, channels },
                                new_shared_item: { enabled: true, channels },
                            },
                        },
                        { headers: { "supported-channels": "email,push" } },
                    ),
                );
            }),
        );

        const wrapper = mount(NotificationsPreferences as object, {
            global: localVue,
            pinia: createPinia(),
        });
        await flushPromises();

        const titles = wrapper.findAll(".category-title").map((title) => title.text());
        expect(titles).toEqual(["Message", "New Shared Item"]);
    });
});

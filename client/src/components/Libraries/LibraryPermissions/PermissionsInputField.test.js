import { composeStories } from "@storybook/vue3-vite";
import { deferred } from "@tests/vitest/deferred";
import { useStoryMount } from "@tests/vitest/stories";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import { sanitizeHtml } from "@/directives/sanitizeHtml";

import * as PermissionsInputFieldStories from "./PermissionsInputField.stories";

import PermissionsInputField from "./PermissionsInputField.vue";

const { NoRolesChosen } = composeStories(PermissionsInputFieldStories);
const mountStory = useStoryMount();
const { server, http } = useServerMock();

function rolesResponse(names) {
    return { roles: names.map((name) => ({ id: name, name })), total: names.length };
}

describe("PermissionsInputField", () => {
    beforeEach(() => {
        vi.mocked(sanitizeHtml).mockClear();
    });

    it("sends the alert through v-sanitize-html's default profile", () => {
        mountStory(NoRolesChosen);

        expect(sanitizeHtml).toHaveBeenCalledWith(NoRolesChosen.args.alert, "default");
    });

    it("ignores search responses that arrive after a newer search", async () => {
        const wrapper = mountStory(NoRolesChosen);
        const field = wrapper.getComponent(PermissionsInputField);
        await vi.waitFor(() =>
            expect(field.vm.fetched_options.map((role) => role.name)).toEqual([
                "alice@example.org",
                "sequencing-core",
                "lab-members",
            ]),
        );
        const pending = {};
        server.use(
            http.get("/api/libraries/{id}/permissions", async ({ query, response }) => {
                const { promise, resolve } = deferred();
                pending[query.get("q") ?? ""] = resolve;
                return response(200).json(await promise);
            }),
        );

        field.vm.searchChanged("b");
        field.vm.searchChanged("bob");
        await vi.waitFor(() => expect(Object.keys(pending)).toEqual(["b", "bob"]));
        pending["bob"](rolesResponse(["bob@test.test"]));
        await flushPromises();
        pending["b"](rolesResponse(["alice@test.test", "bob@test.test"]));
        await flushPromises();

        expect(field.vm.fetched_options.map((role) => role.name)).toEqual(["bob@test.test"]);
    });
});

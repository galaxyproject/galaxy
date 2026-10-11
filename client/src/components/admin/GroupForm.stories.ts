import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { expect } from "storybook/test";

import { http } from "@/api/client/__mocks__/http";

import { ADMIN_GROUPS, ADMIN_ROLES, ADMIN_USER, adminRoleSearch, adminUserSearch } from "./test_fixtures";

import GroupForm from "./GroupForm.vue";

const GROUP = ADMIN_GROUPS[0]!;
const GROUP_MEMBER = { id: ADMIN_USER.id, email: ADMIN_USER.email, url: `${GROUP.url}/users/${ADMIN_USER.id}` };
const ROLE = ADMIN_ROLES[0]!;
const GROUP_ROLE = { id: ROLE.id, name: ROLE.name, url: `${GROUP.url}/roles/${ROLE.id}` };

/** The group's own endpoint and its users and roles endpoints word the same 404 differently. */
const GROUP_NOT_FOUND = { err_msg: "Group with the provided id was not found.", err_code: 404001 };
const ASSOCIATED_GROUP_NOT_FOUND = { err_msg: "Group with the id provided was not found.", err_code: 404001 };

const meta = {
    title: "admin/GroupForm",
    component: GroupForm,
    args: { groupId: GROUP.id },
    parameters: {
        msw: {
            handlers: {
                group: http.get("/api/groups/{group_id}", ({ response }) => response(200).json(GROUP)),
                groupUsers: http.get("/api/groups/{group_id}/users", ({ response }) =>
                    response(200).json([GROUP_MEMBER]),
                ),
                groupRoles: http.get("/api/groups/{group_id}/roles", ({ response }) =>
                    response(200).json([GROUP_ROLE]),
                ),
                userSearch: adminUserSearch(),
                roleSearch: adminRoleSearch(),
                updateGroup: http.put("/api/groups/{group_id}", async ({ request, response }) => {
                    const { name } = await request.json();
                    return response(200).json({ ...GROUP, name: name ?? GROUP.name });
                }),
            },
        },
    },
} satisfies Meta<typeof GroupForm>;

export default meta;
type Story = StoryObj<typeof meta>;

/** An existing group, opened from the admin's groups list, with one member and one role. */
export const ExistingGroup: Story = {};

/** The group was purged before the form opened, so there is nothing to edit. */
export const GroupGone: Story = {
    play: async ({ canvas, step }) => {
        await step("Explain that the group no longer exists", async () => {
            await expect(await canvas.findByRole("alert", {}, { timeout: 5000 })).toHaveTextContent(
                /^Group with the provided id was not found\.$/,
            );
            await expect(canvas.queryByRole("button", { name: "Save" })).not.toBeInTheDocument();
        });
    },
    parameters: {
        msw: {
            handlers: {
                group: http.get("/api/groups/{group_id}", ({ response }) =>
                    response("4XX").json(GROUP_NOT_FOUND, { status: 404 }),
                ),
            },
        },
    },
};

/** The group was purged while the form loaded, so there is nothing left to edit and the form isn't shown. */
export const GroupGoneWhileUsersLoad: Story = {
    play: async ({ canvas, step }) => {
        await step("Refuse to edit a group removed while its members loaded", async () => {
            await expect(await canvas.findByRole("alert", {}, { timeout: 5000 })).toHaveTextContent(
                /^Group with the id provided was not found\.$/,
            );
            await expect(canvas.queryByRole("button", { name: "Save" })).not.toBeInTheDocument();
        });
    },
    parameters: {
        msw: {
            handlers: {
                groupUsers: http.get("/api/groups/{group_id}/users", ({ response }) =>
                    response("4XX").json(ASSOCIATED_GROUP_NOT_FOUND, { status: 404 }),
                ),
            },
        },
    },
};

/** Galaxy failed while loading the group's roles; saving would drop them, so the form isn't shown. */
export const RolesFailToLoad: Story = {
    parameters: {
        msw: {
            handlers: {
                groupRoles: http.get("/api/groups/{group_id}/roles", ({ response }) =>
                    response("5XX").json({ err_msg: "Internal server error.", err_code: 500001 }, { status: 500 }),
                ),
            },
        },
    },
};

export const KeepsSavedNameWhileEditing: Story = {
    play: async ({ canvas, userEvent, step }) => {
        const title = `Group '${GROUP.name}'`;
        await step("Open the saved group", async () => {
            await expect(await canvas.findByText(title, { exact: false }, { timeout: 5000 })).toBeVisible();
        });
        await step("Edit the name while keeping the saved name in the title", async () => {
            const name = canvas.getByDisplayValue(GROUP.name);
            await userEvent.clear(name);
            await userEvent.type(name, "Renamed");
            await expect(name).toHaveValue("Renamed");
            await expect(canvas.getByText(title, { exact: false })).toBeVisible();
        });
    },
};

export const RefusesEmptyName: Story = {
    play: async ({ canvas, userEvent, step }) => {
        await step("Clear the name of the loaded group", async () => {
            const name = await canvas.findByDisplayValue(GROUP.name, {}, { timeout: 5000 });
            await userEvent.clear(name);
            await expect(name).toHaveValue("");
        });
        await step("Ask for a name before saving", async () => {
            await userEvent.click(canvas.getByRole("button", { name: "Save" }));
            await expect(await canvas.findByRole("alert")).toHaveTextContent(/^Please enter a group name\.$/);
            await expect(canvas.getByRole("button", { name: "Save" })).toBeVisible();
        });
    },
};

import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { getFakeRegisteredUser } from "@tests/test-data";
import { withCurrentUser } from "@tests/test-data/currentUser";

import { http } from "@/api/client/__mocks__/http";

import { ADMIN_GROUPS, ADMIN_ROLES, ADMIN_USER, adminGroups, adminRoleSearch } from "./test_fixtures";

import UserRolesGroupsForm from "./UserRolesGroupsForm.vue";

const PRIVATE_ROLE = {
    ...ADMIN_ROLES[0]!,
    id: "fa42ce49be448cfe",
    name: ADMIN_USER.email,
    url: "/api/roles/fa42ce49be448cfe",
    type: "private",
};
const QA_ROLE = {
    ...ADMIN_ROLES[0]!,
    id: "d945ac093e334d10",
    name: "QA",
    url: "/api/roles/d945ac093e334d10",
    description: "Quality assurance team",
};
const ASSIGNABLE_ROLES = [ADMIN_ROLES[0]!, QA_ROLE];

const meta = {
    title: "admin/UserRolesGroupsForm",
    component: UserRolesGroupsForm,
    decorators: [
        withCurrentUser(() =>
            getFakeRegisteredUser({
                id: "91ba11ff309194df",
                email: "admin@example.org",
                username: "admin",
                is_admin: true,
            }),
        ),
    ],
    args: { userId: ADMIN_USER.id },
    parameters: {
        msw: {
            handlers: {
                user: http.get("/api/users/{user_id}", ({ response }) =>
                    response(200).json({
                        ...ADMIN_USER,
                        deleted: false,
                        purged: false,
                        is_admin: false,
                        preferences: {},
                        quota: "unlimited",
                        total_disk_usage: 0,
                        nice_total_disk_usage: "0 bytes",
                    }),
                ),
                userRoles: http.get("/api/users/{user_id}/roles", ({ response }) =>
                    response(200).json([PRIVATE_ROLE, ADMIN_ROLES[0]!]),
                ),
                userGroups: http.get("/api/users/{user_id}/groups", ({ response }) =>
                    response(200).json([
                        { id: ADMIN_GROUPS[0]!.id, name: ADMIN_GROUPS[0]!.name, model_class: "Group" },
                    ]),
                ),
                groups: adminGroups(),
                roleSearch: adminRoleSearch(ASSIGNABLE_ROLES),
                saveRoles: http.put("/api/users/{user_id}/roles", async ({ request, response }) => {
                    const { role_ids } = await request.json();
                    return response(200).json([
                        PRIVATE_ROLE,
                        ...ASSIGNABLE_ROLES.filter(({ id }) => role_ids.includes(id)),
                    ]);
                }),
                saveGroups: http.put("/api/users/{user_id}/groups", async ({ request, response }) => {
                    const { group_ids } = await request.json();
                    return response(200).json(
                        ADMIN_GROUPS.filter(({ id }) => group_ids.includes(id)).map(({ id, name, model_class }) => ({
                            id,
                            name,
                            model_class,
                        })),
                    );
                }),
            },
        },
    },
} satisfies Meta<typeof UserRolesGroupsForm>;

export default meta;
type Story = StoryObj<typeof meta>;

/** An administrator edits Alice's roles and groups; her private role is managed by Galaxy and hidden here. */
export const ExistingUser: Story = {};

/** A failed membership request prevents an empty form from overwriting Alice's memberships. */
export const GroupsUnavailable: Story = {
    parameters: {
        msw: {
            handlers: {
                userGroups: http.get("/api/users/{user_id}/groups", ({ response }) =>
                    response("5XX").json({ err_msg: "Internal server error.", err_code: 500001 }, { status: 500 }),
                ),
            },
        },
    },
};

/** The viewer's administrator access was revoked since loading; saving stops before changing groups. */
export const RoleSaveDenied: Story = {
    parameters: {
        msw: {
            handlers: {
                saveRoles: http.put("/api/users/{user_id}/roles", ({ response }) =>
                    response("4XX").json(
                        { err_msg: "You must be an administrator to access this feature.", err_code: 403006 },
                        { status: 403 },
                    ),
                ),
            },
        },
    },
};

/** Alice was removed after the roles were saved, so the second request fails and the form remains open. */
export const UserGoneBeforeGroupSave: Story = {
    parameters: {
        msw: {
            handlers: {
                saveGroups: http.put("/api/users/{user_id}/groups", ({ response }) =>
                    response("4XX").json({ err_msg: "User not found.", err_code: 404001 }, { status: 404 }),
                ),
            },
        },
    },
};

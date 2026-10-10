import type { Meta, StoryObj } from "@storybook/vue3-vite";

import { http } from "@/api/client/__mocks__/http";

import { ADMIN_GROUPS, ADMIN_USER, adminGroups, adminUserSearch } from "./test_fixtures";

import RoleForm from "./RoleForm.vue";

const ROLE = {
    id: "5f1e3a6c7d2b9e04",
    name: "Data managers",
    description: "Can run data manager tools",
    type: "admin",
    url: "/api/roles/5f1e3a6c7d2b9e04",
    model_class: "Role" as const,
};
const ROLE_MEMBER = { id: ADMIN_USER.id, email: ADMIN_USER.email };
const ROLE_GROUP = ADMIN_GROUPS[0]!;

/** Galaxy's answer when another role already has the name. */
function nameTaken(name: string) {
    return { err_msg: `A role with that name already exists [${name}]`, err_code: 409001 };
}

const meta = {
    title: "admin/RoleForm",
    component: RoleForm,
    parameters: {
        msw: {
            handlers: {
                groups: adminGroups(),
                userSearch: adminUserSearch(),
                createRole: http.post("/api/roles", async ({ request, response }) => {
                    const { name, description } = await request.json();
                    return response(200).json({ ...ROLE, name, description });
                }),
                role: http.get("/api/roles/{id}", ({ response }) => response(200).json(ROLE)),
                roleUsers: http.get("/api/roles/{id}/users", ({ response }) => response(200).json([ROLE_MEMBER])),
                roleGroups: http.get("/api/roles/{id}/groups", ({ response }) =>
                    response(200).json([{ id: ROLE_GROUP.id, name: ROLE_GROUP.name, model_class: "Group" }]),
                ),
                updateRole: http.put("/api/roles/{id}", ({ response }) => response(200).json(ROLE)),
            },
        },
    },
} satisfies Meta<typeof RoleForm>;

export default meta;
type Story = StoryObj<typeof meta>;

/** An empty form for a new role, offering every group. Name, description and type are required. */
export const NewRole: Story = {};

/** The groups can't be loaded, so the form isn't shown and nothing can be created. */
export const GroupsFailToLoad: Story = {
    parameters: {
        msw: {
            handlers: {
                groups: http.get("/api/groups", ({ response }) =>
                    response("5XX").json({ err_msg: "Internal server error.", err_code: 500001 }, { status: 500 }),
                ),
            },
        },
    },
};

/** Another role already has the name typed in, so creating shows Galaxy's refusal above the form. */
export const NewRoleNameTaken: Story = {
    parameters: {
        msw: {
            handlers: {
                createRole: http.post("/api/roles", async ({ request, response }) =>
                    response("4XX").json(nameTaken((await request.json()).name), { status: 409 }),
                ),
            },
        },
    },
};

/** An existing role, with its member and group selected. Its type can't change. */
export const ExistingRole: Story = {
    args: { roleId: ROLE.id },
};

/** The role was deleted while its members loaded; saving would drop them, so the form isn't shown. */
export const ExistingRoleGone: Story = {
    args: { ...ExistingRole.args },
    parameters: {
        msw: {
            handlers: {
                roleUsers: http.get("/api/roles/{id}/users", ({ response }) =>
                    response("4XX").json(
                        { err_msg: "No accessible role found with the id provided.", err_code: 404001 },
                        { status: 404 },
                    ),
                ),
            },
        },
    },
};

/** Another role already has the new name, so saving shows Galaxy's refusal above the form. */
export const ExistingRoleNameTaken: Story = {
    args: { ...ExistingRole.args },
    parameters: {
        msw: {
            handlers: {
                updateRole: http.put("/api/roles/{id}", async ({ request, response }) =>
                    response("4XX").json(nameTaken((await request.json()).name ?? ""), { status: 409 }),
                ),
            },
        },
    },
};

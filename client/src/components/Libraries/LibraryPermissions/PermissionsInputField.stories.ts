import type { Meta, StoryObj } from "@storybook/vue3-vite";

import { http } from "@/api/client/__mocks__/http";

import PermissionsInputField from "./PermissionsInputField.vue";

const ROLES = [
    { id: "f2db41e1fa331b3e", name: "alice@example.org", type: "private" },
    { id: "f597429621d6eb2b", name: "sequencing-core", type: "admin" },
    { id: "1cd8e2f6b131e891", name: "lab-members", type: "admin" },
];

const meta = {
    title: "Libraries/LibraryPermissions/PermissionsInputField",
    component: PermissionsInputField,
    args: {
        id: "33b43b4e7093c91f",
        apiRootUrl: "/api/libraries",
    },
    parameters: {
        msw: {
            handlers: {
                availableRoles: http.get("/api/libraries/{id}/permissions", ({ response }) =>
                    response(200).json({ roles: ROLES, page: 1, page_limit: 10, total: ROLES.length }),
                ),
            },
        },
    },
} satisfies Meta<typeof PermissionsInputField>;

export default meta;
type Story = StoryObj<typeof meta>;

/** The library's access picker with no roles set yet, which leaves the library unrestricted. */
export const NoRolesChosen: Story = {
    args: {
        title: "Roles that can access the library",
        permission_type: "access_library_role_list",
        initial_value: [],
        alert: "User with <strong>any</strong> of these roles can access this library. If there are no access roles set on the library it is considered <strong>unrestricted</strong>.",
    },
};

/** The manage picker with two roles already granted. */
export const RolesChosen: Story = {
    args: {
        title: "Roles that can manage this library",
        permission_type: "manage_library_role_list",
        // the library page passes the granted roles without their type
        initial_value: ROLES.slice(1).map(({ id, name }) => ({ id, name })),
        alert: "User with <strong>any</strong> of these roles can manage this library.",
    },
};

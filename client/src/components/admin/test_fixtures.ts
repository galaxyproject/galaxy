import type { components } from "@/api";
import { http } from "@/api/client/__mocks__/http";

type GroupResponse = components["schemas"]["GroupResponse"];

/** The groups an admin form offers to add a role, quota or user to. */
export const ADMIN_GROUPS: GroupResponse[] = [
    { id: "1cd8e2f6b131e891", name: "Bioinformatics core", url: "/api/groups/1cd8e2f6b131e891", model_class: "Group" },
    { id: "ebfb8f50c6abde6d", name: "Teaching", url: "/api/groups/ebfb8f50c6abde6d", model_class: "Group" },
];

/** Answers the admin forms' request for every group. */
export function adminGroups(groups: GroupResponse[] = ADMIN_GROUPS) {
    return http.get("/api/groups", ({ response }) => response(200).json(groups));
}

/** A user an admin form finds by email. */
export const ADMIN_USER = { id: "f2db41e1fa331b3e", email: "alice@example.org", username: "alice" };

/** Answers the admin forms' user search with the users whose email contains the typed text. */
export function adminUserSearch(users = [ADMIN_USER]) {
    return http.get("/api/users", ({ query, response }) =>
        response(200).json(users.filter((user) => user.email.includes(query.get("f_email") ?? ""))),
    );
}

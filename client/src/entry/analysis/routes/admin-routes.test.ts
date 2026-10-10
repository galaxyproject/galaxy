import { describe, expect, it, vi } from "vitest";
import { createMemoryHistory, createRouter, type RouteLocationNormalizedLoaded } from "vue-router";

import AdminRoutes from "./admin-routes";

vi.mock("@/app", () => ({
    getGalaxyInstance: () => ({
        config: {
            registration_warning_message: "warning",
            mailing_join_addr: "join@example.org",
            server_mail_configured: true,
        },
        session_csrf_token: "token",
    }),
}));

function resolveProps(route: RouteLocationNormalizedLoaded) {
    const props = route.matched.at(-1)?.props.default;
    return typeof props === "function" ? props(route) : props;
}

async function routeTo(path: string) {
    const router = createRouter({ history: createMemoryHistory(), routes: AdminRoutes });
    await router.push(path);
    return router.currentRoute.value;
}

describe("admin routes", () => {
    it("marks admin children as requiring admin", async () => {
        const route = await routeTo("/admin/jobs");
        expect(route.meta.requiresAdmin).toBe(true);
    });

    it("passes the query message to admin grids", async () => {
        const route = await routeTo("/admin/users?message=Saved");
        expect(resolveProps(route)).toMatchObject({ gridMessage: "Saved" });
    });

    it("passes the query id to admin forms", async () => {
        expect(resolveProps(await routeTo("/admin/form/edit_quota?id=Q1"))).toEqual({ quotaId: "Q1" });
        expect(resolveProps(await routeTo("/admin/form/edit_form?id=F1"))).toEqual({
            url: "/forms/edit_form?id=F1",
            redirect: "/admin/forms",
        });
    });

    it("passes the registration config to the user create form", async () => {
        expect(resolveProps(await routeTo("/admin/users/create"))).toEqual({
            redirect: "/admin/users",
            registrationWarningMessage: "warning",
            mailingJoinAddr: "join@example.org",
            serverMailConfigured: true,
            sessionCsrfToken: "token",
        });
    });

    it("routes data manager jobs by name with the id as a prop", async () => {
        const route = await routeTo("/admin/data_manager/jobs/D1");
        expect(route.name).toEqual("DataManagerJobs");
        expect(route.matched.at(-1)?.props.default).toBe(true);
    });
});

import { describe, expect, it } from "vitest";

import adminUsers from "./adminUsers";

const emailField = adminUsers.fields[0];

function operation(title) {
    const found = emailField.operations.find((candidate) => candidate.title === title);
    if (!found) {
        throw new Error(`No "${title}" operation`);
    }
    return found;
}

function config(options) {
    return { value: options };
}

describe("adminUsers grid configuration", () => {
    it("declares the user columns, starting with the email operations column", () => {
        expect(adminUsers.fields.map((field) => field.key)).toEqual([
            "email",
            "username",
            "last_login",
            "disk_usage",
            "status",
            "create_time",
            "active",
            "groups",
            "roles",
            "external",
        ]);
        expect(emailField.type).toBe("operations");
    });

    it.each([
        { purged: false, shown: true },
        { purged: true, shown: false },
    ])("shows the email operations when purged is $purged: $shown", ({ purged, shown }) => {
        expect(emailField.condition({ purged })).toBe(shown);
    });

    it("lists the user operations in menu order", () => {
        expect(emailField.operations.map((candidate) => candidate.title)).toEqual([
            "Manage Information",
            "Manage Roles and Groups",
            "Reset Password",
            "Recalculate Disk Usage",
            "Activate",
            "Send Activation Email",
            "Generate New API Key",
            "Impersonate User",
            "Delete",
            "Permanently Delete",
            "Restore",
        ]);
    });

    describe.each([
        "Manage Information",
        "Manage Roles and Groups",
        "Reset Password",
        "Recalculate Disk Usage",
        "Generate New API Key",
    ])("%s", (title) => {
        it.each([
            { deleted: false, shown: true },
            { deleted: true, shown: false },
        ])("is shown when deleted is $deleted: $shown", ({ deleted, shown }) => {
            expect(operation(title).condition({ deleted })).toBe(shown);
        });
    });

    describe.each([
        ["Activate", "user_activation_on"],
        ["Send Activation Email", "user_activation_on"],
        ["Impersonate User", "allow_user_impersonation"],
        ["Delete", "allow_user_deletion"],
    ])("%s", (title, option) => {
        it.each([
            { deleted: false, enabled: true, shown: true },
            { deleted: false, enabled: false, shown: false },
            { deleted: true, enabled: true, shown: false },
            { deleted: true, enabled: false, shown: false },
        ])(`is shown when deleted is $deleted and ${option} is $enabled: $shown`, ({ deleted, enabled, shown }) => {
            expect(operation(title).condition({ deleted }, config({ [option]: enabled }))).toBe(shown);
        });
    });

    describe.each(["Permanently Delete", "Restore"])("%s", (title) => {
        it.each([
            { deleted: true, purged: false, allowed: true, shown: true },
            { deleted: true, purged: false, allowed: false, shown: false },
            { deleted: true, purged: true, allowed: true, shown: false },
            { deleted: true, purged: true, allowed: false, shown: false },
            { deleted: false, purged: false, allowed: true, shown: false },
            { deleted: false, purged: false, allowed: false, shown: false },
            { deleted: false, purged: true, allowed: true, shown: false },
            { deleted: false, purged: true, allowed: false, shown: false },
        ])(
            "is shown when deleted is $deleted, purged is $purged and allow_user_deletion is $allowed: $shown",
            ({ deleted, purged, allowed, shown }) => {
                expect(operation(title).condition({ deleted, purged }, config({ allow_user_deletion: allowed }))).toBe(
                    shown,
                );
            },
        );
    });
});

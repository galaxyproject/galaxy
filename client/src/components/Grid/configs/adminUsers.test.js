import adminUsers from "./adminUsers";

describe("AdminUsers", () => {
    it("configuration", async () => {
        const fields = adminUsers.fields;
        expect(fields.length).toBe(10);
        const fieldEmail = fields[0];
        expect(fieldEmail.key).toBe("email");
        expect(fieldEmail.type).toBe("operations");
        for (const purged of [true, false]) {
            expect(fieldEmail.condition({ purged })).toBe(!purged);
        }
        const ops = fieldEmail.operations;
        const titles = [
            "Information",
            "Roles",
            "Reset",
            "Recalculate",
            "Activate",
            "Send",
            "Key",
            "Impersonate",
            "Delete",
            "Permanently Delete",
            "Restore",
        ];
        titles.forEach((title, index) => {
            expect(ops[index].title).toContain(title);
        });
        for (const a of [true, false]) {
            expect(ops[0].condition({ deleted: !a })).toBe(a);
            expect(ops[1].condition({ deleted: !a })).toBe(a);
            expect(ops[2].condition({ deleted: !a })).toBe(a);
            expect(ops[3].condition({ deleted: !a })).toBe(a);
            expect(ops[6].condition({ deleted: !a })).toBe(a);
            for (const b of [true, false]) {
                expect(ops[4].condition({ deleted: !a }, { value: { user_activation_on: b } })).toBe(a && b);
                expect(ops[5].condition({ deleted: !a }, { value: { user_activation_on: b } })).toBe(a && b);
                expect(ops[7].condition({ deleted: !a }, { value: { allow_user_impersonation: b } })).toBe(a && b);
                expect(ops[8].condition({ deleted: !a }, { value: { allow_user_deletion: b } })).toBe(a && b);
                for (const c of [true, false]) {
                    expect(ops[9].condition({ deleted: a, purged: !b }, { value: { allow_user_deletion: c } })).toBe(
                        a && b && c
                    );
                    expect(ops[10].condition({ deleted: a, purged: !b }, { value: { allow_user_deletion: c } })).toBe(
                        a && b && c
                    );
                }
            }
        }
    });
});

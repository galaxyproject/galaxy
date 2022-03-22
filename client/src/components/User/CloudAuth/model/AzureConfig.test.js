import { AzureConfig } from "./AzureConfig";

describe("AzureConfig", () => {
    it("should instantiate", () => {
        const instance = new AzureConfig();
        expect(instance).toBeTruthy();
        expect(!instance.dirty).toBeTruthy();
        expect(!instance.valid).toBeTruthy();
    });

    describe("client_secret", () => {
        it("should validate client_secret", () => {
            const instance = new AzureConfig();
            instance.client_secret = "abc";
            expect(instance.fieldValid("client_secret")).toBeTruthy();
        });

        it("should invalidate client_secret", () => {
            const instance = new AzureConfig();
            instance.client_secret = "";
            expect(!instance.fieldValid("client_secret")).toBeTruthy();
        });
    });

    describe("tenant_id", () => {
        it("should validate tenant_id", () => {
            const validTenantId = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx";
            const instance = new AzureConfig();
            instance.tenant_id = validTenantId;
            expect(instance.fieldValid("tenant_id")).toBeTruthy();
        });

        it("should invalidate tenant_id", () => {
            const instance = new AzureConfig();
            instance.tenant_id = "";
            expect(!instance.fieldValid("tenant_id")).toBeTruthy();
            instance.tenant_id = "asdfa";
            expect(!instance.fieldValid("tenant_id")).toBeTruthy();
        });
    });

    describe("client_id", () => {
        it("should validate client_id", () => {
            const validClientId = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx";
            const instance = new AzureConfig();
            instance.client_id = validClientId;
            expect(instance.fieldValid("client_id")).toBeTruthy();
        });

        it("should invalidate client_id", () => {
            const instance = new AzureConfig();
            instance.client_id = "";
            expect(!instance.fieldValid("client_id")).toBeTruthy();
            instance.client_id = "asdf";
            expect(!instance.fieldValid("client_id")).toBeTruthy();
        });
    });
});

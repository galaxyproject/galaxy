import { AzureConfig } from "./AzureConfig";

describe("AzureConfig", () => {

    it("should instantiate", () => {
        let instance = new AzureConfig();
        assert(instance);
        assert(!instance.dirty);
        assert(!instance.valid);
    })


    describe("client_secret", () => {

        it("should validate client_secret", () => {
            let instance = new AzureConfig();
            instance.client_secret = "abc";
            assert(instance.fieldValid("client_secret"));
        })
    
        it("should invalidate client_secret", () => {
            let instance = new AzureConfig();
            instance.client_secret = "";
            assert(!instance.fieldValid("client_secret"));
        })

    })


    describe("tenant_id", () => {

        it("should validate tenant_id", () => {
            let validTenantId = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx";
            let instance = new AzureConfig();
            instance.tenant_id = validTenantId;
            assert(instance.fieldValid("tenant_id"));
        })
    
        it("should invalidate tenant_id", () => {
            let instance = new AzureConfig();
            instance.tenant_id = "";
            assert(!instance.fieldValid("tenant_id"));
            instance.tenant_id = "asdfa";
            assert(!instance.fieldValid("tenant_id"));
        })

    })


    describe("client_id", () => {

        it("should validate client_id", () => {
            let validClientId = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx";
            let instance = new AzureConfig();
            instance.client_id = validClientId;
            assert(instance.fieldValid("client_id"));
        })
    
        it("should invalidate client_id", () => {
            let instance = new AzureConfig();
            instance.client_id = "";
            assert(!instance.fieldValid("client_id"));
            instance.client_id = "asdf";
            assert(!instance.fieldValid("client_id"));
        })

    })


})

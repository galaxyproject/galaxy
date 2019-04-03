import { AzureConfig } from "./AzureConfig";

describe("AzureConfig", () => {

    it("should instantiate", () => {
        let instance = new AzureConfig();
        assert(instance);
        assert(!instance.dirty);
        assert(!instance.valid);
    })

    it("should validate client_secret", () => {
        let instance = new AzureConfig();
        instance.tenant_id = "abc";
        instance.client_secret = "abc";
        assert(instance.fieldValid("client_secret"));
        assert(!instance.fieldValid("tenant_id"));
        assert(!instance.fieldValid("client_id"));
    })

})
import { AwsConfig } from "./AwsConfig";

describe("AwsConfig", () => {

    it("should instantiate", () => {
        let instance = new AwsConfig();
        assert(instance);
        assert(!instance.dirty);
        assert(!instance.valid);
    })

    it("should validate role_arn", () => {
        let instance = new AwsConfig();
        instance.role_arn = "abc";
        assert(instance.fieldValid("role_arn"));
    })

    it("should invalidate role_arn", () => {
        let instance = new AwsConfig();
        instance.role_arn = "";
        assert(!instance.fieldValid("role_arn"));
    })

})

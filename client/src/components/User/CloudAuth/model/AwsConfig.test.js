import { AwsConfig } from "./AwsConfig";

describe("AwsConfig", () => {
    it("should instantiate", () => {
        const instance = new AwsConfig();
        expect(instance).toBeTruthy();
        expect(!instance.dirty).toBeTruthy();
        expect(!instance.valid).toBeTruthy();
    });

    it("should validate role_arn", () => {
        const instance = new AwsConfig();
        instance.role_arn = "abc";
        expect(instance.fieldValid("role_arn")).toBeTruthy();
    });

    it("should invalidate role_arn", () => {
        const instance = new AwsConfig();
        instance.role_arn = "";
        expect(!instance.fieldValid("role_arn")).toBeTruthy();
    });
});

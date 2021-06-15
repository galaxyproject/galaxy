import { Credential } from "./Credential";

describe("Credential model", () => {
    describe("basic model props", () => {
        it("should exist", () => {
            expect(Credential).toBeTruthy();
        });

        it("should build with defaults", () => {
            const instance = new Credential();
            expect(instance).toBeTruthy();
        });

        it("should build with props", () => {
            const description = "i am the test description";
            const props = { description };
            const instance = new Credential(props);
            expect(instance).toBeTruthy();
            expect(instance.description == description).toBeTruthy();
        });

        it("default config object should be AWS", () => {
            const instance = new Credential();
            expect("role_arn" in instance.config).toBeTruthy();
            expect(instance.config.constructor.name == "AwsConfig").toBeTruthy();
        });

        it("should load a different config object given the right provider", () => {
            const provider = "azure";
            const props = { provider };
            const instance = new Credential(props);
            expect(instance.provider == provider).toBeTruthy();
            expect(instance.config.constructor.name == "AzureConfig").toBeTruthy();
        });

        it("should dynamically switch config objects as resourceProvider is changed", () => {
            const instance = new Credential();
            expect(instance.provider == "aws").toBeTruthy();
            instance.resourceProvider = "azure";
            expect(instance.config.constructor.name == "AzureConfig").toBeTruthy();
            instance.resourceProvider = "aws";
            expect(instance.config.constructor.name == "AwsConfig").toBeTruthy();
        });
    });

    describe("dirty state", () => {
        it("should flag as dirty when a prop is changed", () => {
            const instance = new Credential();
            instance.description = "foo";
            expect(instance.dirty).toBeTruthy();
        });

        it("should flag as clean when a prop is restored", () => {
            const instance = new Credential();
            instance.description = "foo";
            expect(instance.dirty).toBeTruthy();
            instance.description = "";
            expect(!instance.dirty).toBeTruthy();
        });

        it("should not flag as dirty when a transient prop is changed", () => {
            const instance = new Credential();
            instance.loading = true;
            expect(!instance.dirty).toBeTruthy();
        });
    });

    describe("validation", () => {
        it("a new object should be invalid", () => {
            const instance = new Credential();
            expect(!instance.valid).toBeTruthy();
        });

        it("it should become valid when props are assigned", () => {
            const instance = new Credential();
            instance.authn_id = "floob";
            instance.resourceProvider = "aws";
            instance.config.role_arn = "abc";
            expect(instance.valid).toBeTruthy();
        });

        it("it should be valid when initialized with correct props", () => {
            const props = {
                authn_id: "asdfasdf",
                provider: "aws",
                config: {
                    role_arn: "floobar",
                },
            };
            const instance = new Credential(props);
            expect(instance.valid).toBeTruthy();
        });

        it("should be invalid when bad props assigned", () => {
            const props = {
                authn_id: "asdfasdf",
                provider: "aws",
                config: {
                    role_arn: "",
                },
            };
            const instance = new Credential(props);
            expect(!instance.valid).toBeTruthy();
        });
    });
});

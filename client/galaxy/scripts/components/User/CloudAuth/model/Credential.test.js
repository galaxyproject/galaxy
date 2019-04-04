import { Credential } from "./Credential";

describe("Credential model", () => {

    describe("basic model props", () => {

        it("should exist", () => {
            assert(Credential);
        })
    
        it("should build with defaults", () => {
            let instance = new Credential();
            assert(instance);
        })
    
        it("should build with props", () => {
            let description = "i am the test description";
            let props = { description };
            let instance = new Credential(props);
            assert(instance);
            assert(instance.description == description);
        })
    
        it("default config object should be AWS", () => {
            let instance = new Credential();
            assert('role_arn' in instance.config, "Missing role_arn prop");
            assert(instance.config.constructor.name == "AwsConfig");
        })
    
        it("should load a different config object given the right provider", () => {
            let provider = 'azure';
            let props = { provider };
            let instance = new Credential(props);
            assert(instance.provider == provider);
            assert(instance.config.constructor.name == "AzureConfig");
        })
    
        it("should dynamically switch config objects as resourceProvider is changed", () => {
            let instance = new Credential();
            assert(instance.provider == 'aws', "Should default to AWS config' ");
            instance.resourceProvider = 'azure';
            assert(instance.config.constructor.name == "AzureConfig", "Should have been AzureConfig");
            instance.resourceProvider = 'aws';
            assert(instance.config.constructor.name == "AwsConfig", "Should be AWS Config again");
        })
    })

    describe("dirty state", () => {

        it("should flag as dirty when a prop is changed", () => {
            let instance = new Credential();
            instance.description = "foo";
            assert(instance.dirty);
        })

        it("should flag as clean when a prop is restored", () => {
            let instance = new Credential();
            instance.description = 'foo';
            assert(instance.dirty);
            instance.description = "";
            assert(!instance.dirty);
        })

        it("should not flag as dirty when a transient prop is changed", () => {
            let instance = new Credential();
            instance.loading = true;
            assert(!instance.dirty);
        })

    })

    describe("validation", () => {

        it("a new object should be invalid", () => {
            let instance = new Credential();
            assert(!instance.valid);
        })

        it("it should become valid when props are assigned", () => {
            let instance = new Credential();
            instance.authn_id = "floob";
            instance.resourceProvider = 'aws';
            instance.config.role_arn = "abc";
            assert(instance.valid);
        })

        it("it should be valid when initialized with correct props", () => {
            let props = {
                authn_id: "asdfasdf",
                provider: 'aws',
                config: {
                    role_arn: "floobar"
                }
            }
            let instance = new Credential(props);
            assert(instance.valid);
        })

        it("should be invalid when bad props assigned", () => {
            let props = {
                authn_id: "asdfasdf",
                provider: 'aws',
                config: {
                    role_arn: ""
                }
            }
            let instance = new Credential(props);
            assert(!instance.valid);
        })

    })

})

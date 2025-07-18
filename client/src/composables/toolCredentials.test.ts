import type { ServiceCredentialsDefinition, ServiceVariableDefinition } from "@/api/users";

import { useToolCredentials } from "./toolCredentials";

describe("useToolCredentials", () => {
    const mockSecretDefinition: ServiceVariableDefinition = {
        name: "api_key",
        label: "API Key",
        description: "Your service API key",
        optional: false,
    };

    const mockOptionalSecretDefinition: ServiceVariableDefinition = {
        name: "optional_key",
        label: "Optional Key",
        description: "Optional service key",
        optional: true,
    };

    const mockVariableDefinition: ServiceVariableDefinition = {
        name: "base_url",
        label: "Base URL",
        description: "Service base URL",
        optional: false,
    };

    const mockOptionalVariableDefinition: ServiceVariableDefinition = {
        name: "timeout",
        label: "Timeout",
        description: "Request timeout",
        optional: true,
    };

    const mockServiceWithRequiredCredentials: ServiceCredentialsDefinition[] = [
        {
            name: "test-service",
            version: "1.0",
            label: "Test Service",
            description: "A test service with required credentials",
            secrets: [mockSecretDefinition],
            variables: [mockVariableDefinition],
        },
    ];

    const mockServiceWithOptionalCredentials: ServiceCredentialsDefinition[] = [
        {
            name: "optional-service",
            version: "1.0",
            label: "Optional Service",
            description: "A test service with optional credentials",
            secrets: [mockOptionalSecretDefinition],
            variables: [mockOptionalVariableDefinition],
        },
    ];

    const mockServiceWithMixedCredentials: ServiceCredentialsDefinition[] = [
        {
            name: "mixed-service",
            version: "1.0",
            label: "Mixed Service",
            description: "A test service with both required and optional credentials",
            secrets: [mockSecretDefinition, mockOptionalSecretDefinition],
            variables: [mockVariableDefinition, mockOptionalVariableDefinition],
        },
    ];

    it("correctly initializes source credentials definition", () => {
        const { sourceCredentialsDefinition } = useToolCredentials("test-tool", mockServiceWithRequiredCredentials);

        expect(sourceCredentialsDefinition.value.sourceType).toBe("tool");
        expect(sourceCredentialsDefinition.value.sourceId).toBe("test-tool");
        expect(sourceCredentialsDefinition.value.services.size).toBe(1);
    });

    it("detects services with required credentials", () => {
        const { hasSomeRequiredCredentials, hasSomeOptionalCredentials } = useToolCredentials(
            "test-tool",
            mockServiceWithRequiredCredentials
        );

        expect(hasSomeRequiredCredentials.value).toBe(true);
        expect(hasSomeOptionalCredentials.value).toBe(false);
    });

    it("detects services with optional credentials", () => {
        const { hasSomeRequiredCredentials, hasSomeOptionalCredentials } = useToolCredentials(
            "test-tool",
            mockServiceWithOptionalCredentials
        );

        expect(hasSomeRequiredCredentials.value).toBe(false);
        expect(hasSomeOptionalCredentials.value).toBe(true);
    });

    it("detects services with mixed credentials", () => {
        const { hasSomeRequiredCredentials, hasSomeOptionalCredentials } = useToolCredentials(
            "test-tool",
            mockServiceWithMixedCredentials
        );

        expect(hasSomeRequiredCredentials.value).toBe(true);
        expect(hasSomeOptionalCredentials.value).toBe(true);
    });

    it("correctly reports when tool has any credentials", () => {
        const { hasAnyCredentials: hasCredentials } = useToolCredentials(
            "test-tool",
            mockServiceWithRequiredCredentials
        );
        const { hasAnyCredentials: hasNoCredentials } = useToolCredentials("empty-tool", []);

        expect(hasCredentials.value).toBe(true);
        expect(hasNoCredentials.value).toBe(false);
    });

    it("provides accurate services count", () => {
        const { servicesCount } = useToolCredentials("test-tool", mockServiceWithRequiredCredentials);

        expect(servicesCount.value).toBe(1);
    });

    it("handles empty credentials definition", () => {
        const { hasAnyCredentials, servicesCount, hasSomeRequiredCredentials, hasSomeOptionalCredentials } =
            useToolCredentials("empty-tool", []);

        expect(hasAnyCredentials.value).toBe(false);
        expect(servicesCount.value).toBe(0);
        expect(hasSomeRequiredCredentials.value).toBe(false);
        expect(hasSomeOptionalCredentials.value).toBe(false);
    });
});

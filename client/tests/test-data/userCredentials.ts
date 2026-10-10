import type { ServiceCredentialGroupResponse, UserServiceCredentialsResponse } from "@/api/userCredentials";

export function getFakeServiceCredentialGroup(
    overrides: Partial<ServiceCredentialGroupResponse> = {},
): ServiceCredentialGroupResponse {
    return {
        id: "group-123",
        name: "Test Group",
        update_time: "2023-01-01T00:00:00Z",
        variables: [{ name: "bucket_name", value: "my-bucket" }],
        secrets: [
            { name: "access_key", is_set: true },
            { name: "secret_key", is_set: true },
        ],
        ...overrides,
    };
}

export function getFakeUserServiceCredentials(
    overrides: Partial<UserServiceCredentialsResponse> = {},
): UserServiceCredentialsResponse {
    const group = getFakeServiceCredentialGroup();
    return {
        id: "service-123",
        user_id: "test-user-123",
        source_type: "tool",
        source_id: "test-tool",
        source_version: "1.0.0",
        name: "aws-s3",
        version: "1.0",
        current_group_id: group.id,
        groups: [group],
        ...overrides,
    };
}

import { type components, GalaxyApi } from "@/api";
import { ApiError, rethrowSimpleWithStatus } from "@/utils/simple-error";

export type DeviceAuthorizationDetails = components["schemas"]["DeviceAuthorizationDetails"];

/** Why a code can no longer be approved or denied, from the `reason` Galaxy adds to the error. */
export type DeviceAuthorizationErrorReason = "unknown" | "expired" | "used";

const ERROR_REASONS: DeviceAuthorizationErrorReason[] = ["unknown", "expired", "used"];

export class DeviceAuthorizationError extends ApiError {
    /** Set when the code itself is the problem; unset for other errors, which may be worth retrying. */
    reason?: DeviceAuthorizationErrorReason;
}

function rethrowWithReason(error: unknown, response: Response): never {
    try {
        rethrowSimpleWithStatus(error, response);
    } catch (e) {
        if (!(e instanceof ApiError)) {
            throw e;
        }
        const deviceError = new DeviceAuthorizationError(e.message, e.status);
        const reason = (error as { reason?: unknown } | null)?.reason;
        deviceError.reason = ERROR_REASONS.find((known) => known === reason);
        throw deviceError;
    }
}

export async function fetchDeviceAuthorization(userCode: string): Promise<DeviceAuthorizationDetails> {
    const { data, error, response } = await GalaxyApi().GET("/api/oauth/device_authorization/{user_code}", {
        params: { path: { user_code: userCode } },
    });

    if (error) {
        rethrowWithReason(error, response);
    }

    return data;
}

export async function decideDeviceAuthorization(userCode: string, approve: boolean) {
    const { error, response } = await GalaxyApi().PUT("/api/oauth/device_authorization/{user_code}", {
        params: { path: { user_code: userCode } },
        body: { approve },
    });

    if (error) {
        rethrowWithReason(error, response);
    }
}

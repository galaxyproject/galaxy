import { afterEach, describe, expect, it, vi } from "vitest";

import { Toast } from "@/composables/toast";

import { useCallbacks } from "./datasetPermissions";

vi.mock("@/composables/toast", () => {
    const toast = { error: vi.fn(), success: vi.fn() };
    return { Toast: toast, useToast: () => toast };
});

describe("dataset permissions callbacks", () => {
    afterEach(() => vi.clearAllMocks());

    it("handles a denied initial permissions request", async () => {
        const error = new Error("Request failed with status code 403");
        const init = vi.fn().mockRejectedValue(error);

        useCallbacks(init);
        await vi.waitFor(() => expect(Toast.error).toHaveBeenCalledWith(error.message));
        expect(init).toHaveBeenCalledTimes(1);
    });

    it("handles a denied reload after saving permissions", async () => {
        const error = new Error("Request failed with status code 403");
        const init = vi.fn().mockResolvedValueOnce(undefined).mockRejectedValueOnce(error);
        const { onSuccess } = useCallbacks(init);

        await onSuccess({ data: { message: "Saved" } } as never);

        expect(Toast.success).toHaveBeenCalledWith("Saved");
        expect(Toast.error).toHaveBeenCalledWith(error.message);
    });
});

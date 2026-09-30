import { afterEach, describe, expect, it, vi } from "vitest";

import { Toast } from "@/composables/toast";

import { useCallbacks } from "./datasetPermissions";

vi.mock("@/composables/toast", () => {
    const toast = { error: vi.fn(), success: vi.fn() };
    return { Toast: toast, useToast: () => toast };
});

describe("dataset permissions callbacks", () => {
    afterEach(() => vi.clearAllMocks());

    it("tracks a successful initial load", async () => {
        const init = vi.fn().mockResolvedValue(undefined);

        const { loading, loadError } = useCallbacks(init);
        expect(loading.value).toBe(true);
        await vi.waitFor(() => expect(loading.value).toBe(false));
        expect(loadError.value).toBe("");
    });

    it("handles a denied initial permissions request", async () => {
        const error = new Error("Request failed with status code 403");
        const init = vi.fn().mockRejectedValue(error);

        const { loading, loadError } = useCallbacks(init);
        await vi.waitFor(() => expect(loading.value).toBe(false));
        expect(loadError.value).toBe(error.message);
        expect(Toast.error).not.toHaveBeenCalled();
        expect(init).toHaveBeenCalledTimes(1);
    });

    it("handles a denied reload after saving permissions", async () => {
        const error = new Error("Request failed with status code 403");
        const init = vi.fn().mockResolvedValueOnce(undefined).mockRejectedValueOnce(error);
        const { loadError, onSuccess } = useCallbacks(init);

        await onSuccess({ data: { message: "Saved" } } as never);

        expect(Toast.success).toHaveBeenCalledWith("Saved");
        expect(loadError.value).toBe(error.message);
        expect(Toast.error).not.toHaveBeenCalled();
    });
});

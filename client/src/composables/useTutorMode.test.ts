import { beforeEach, describe, expect, it, vi } from "vitest";

import { useTutorMode } from "./useTutorMode";

const mockGET = vi.fn();
const mockPOST = vi.fn();

vi.mock("@/api", () => ({
    GalaxyApi: () => ({ GET: mockGET, POST: mockPOST }),
}));

describe("useTutorMode", () => {
    beforeEach(() => {
        mockGET.mockReset();
        mockPOST.mockReset();
    });

    it("defaults to tutor mode off", () => {
        const { tutorModeEnabled, scaffoldingLevel } = useTutorMode();
        expect(tutorModeEnabled.value).toBe(false);
        expect(scaffoldingLevel.value).toBeNull();
    });

    it("fetchTutorState applies the backend learning state", async () => {
        mockGET.mockResolvedValue({
            data: { tutor_mode_enabled: true, scaffolding_level: 2 },
            error: undefined,
        });
        const { tutorModeEnabled, scaffoldingLevel, fetchTutorState } = useTutorMode();
        await fetchTutorState();
        expect(mockGET).toHaveBeenCalledWith("/api/chat/tutor/state");
        expect(tutorModeEnabled.value).toBe(true);
        expect(scaffoldingLevel.value).toBe(2);
    });

    it("setTutorMode posts a bare boolean and updates from the response", async () => {
        mockPOST.mockResolvedValue({
            data: { enabled: true, state: { tutor_mode_enabled: true, scaffolding_level: 3 } },
            error: undefined,
        });
        const { tutorModeEnabled, scaffoldingLevel, setTutorMode } = useTutorMode();
        await setTutorMode(true);
        expect(mockPOST).toHaveBeenCalledWith("/api/chat/tutor/mode", { body: { enabled: true } });
        expect(tutorModeEnabled.value).toBe(true);
        expect(scaffoldingLevel.value).toBe(3);
    });

    it("rethrows API errors", async () => {
        mockGET.mockResolvedValue({ data: undefined, error: { err_msg: "boom" } });
        const { fetchTutorState } = useTutorMode();
        await expect(fetchTutorState()).rejects.toBeTruthy();
    });

    it("shows a toggle right away and puts it back when the server refuses", async () => {
        let reject: (reason: unknown) => void = () => {};
        mockPOST.mockReturnValue(new Promise((_, r) => (reject = r)));
        const { tutorModeEnabled, loading, setTutorMode } = useTutorMode();

        const pending = setTutorMode(true);
        // The switch has already moved, so it has to move back if the request fails.
        expect(tutorModeEnabled.value).toBe(true);
        expect(loading.value).toBe(true);

        reject(new Error("offline"));
        await expect(pending).rejects.toBeTruthy();
        expect(tutorModeEnabled.value).toBe(false);
        expect(loading.value).toBe(false);
    });

    it("does not let a slow initial fetch undo a toggle", async () => {
        let resolveGet: (value: unknown) => void = () => {};
        mockGET.mockReturnValue(new Promise((r) => (resolveGet = r)));
        mockPOST.mockResolvedValue({ data: { enabled: true, state: { tutor_mode_enabled: true } }, error: undefined });
        const { tutorModeEnabled, fetchTutorState, setTutorMode } = useTutorMode();

        const fetching = fetchTutorState();
        await setTutorMode(true);
        resolveGet({ data: { tutor_mode_enabled: false, scaffolding_level: 3 }, error: undefined });
        await fetching;

        expect(tutorModeEnabled.value).toBe(true);
    });
});

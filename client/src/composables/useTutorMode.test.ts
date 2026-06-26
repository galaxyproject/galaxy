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
        const { tutorModeEnabled, scaffoldingLevel, expertiseLevel } = useTutorMode();
        expect(tutorModeEnabled.value).toBe(false);
        expect(scaffoldingLevel.value).toBeNull();
        expect(expertiseLevel.value).toBeNull();
    });

    it("fetchTutorState applies the backend learning state", async () => {
        mockGET.mockResolvedValue({
            data: { tutor_mode_enabled: true, scaffolding_level: 2, expertise_level: "intermediate" },
            error: undefined,
        });
        const { tutorModeEnabled, scaffoldingLevel, expertiseLevel, fetchTutorState } = useTutorMode();
        await fetchTutorState();
        expect(mockGET).toHaveBeenCalledWith("/api/chat/tutor/state");
        expect(tutorModeEnabled.value).toBe(true);
        expect(scaffoldingLevel.value).toBe(2);
        expect(expertiseLevel.value).toBe("intermediate");
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

    it("toggleTutorMode flips the current state", async () => {
        mockPOST.mockResolvedValue({
            data: { enabled: true, state: { tutor_mode_enabled: true } },
            error: undefined,
        });
        const { toggleTutorMode, tutorModeEnabled } = useTutorMode();
        await toggleTutorMode();
        expect(mockPOST).toHaveBeenCalledWith("/api/chat/tutor/mode", { body: { enabled: true } });
        expect(tutorModeEnabled.value).toBe(true);
    });

    it("rethrows API errors", async () => {
        mockGET.mockResolvedValue({ data: undefined, error: { err_msg: "boom" } });
        const { fetchTutorState } = useTutorMode();
        await expect(fetchTutorState()).rejects.toBeTruthy();
    });
});

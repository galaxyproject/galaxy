import { beforeEach, describe, expect, it, vi } from "vitest"

const addToast = vi.fn()
vi.mock("@galaxyproject/galaxy-ui", () => ({ useToast: () => ({ addToast }) }))

const { notify, notifyOnCatch } = await import("./util")

describe("notify", () => {
    beforeEach(() => {
        addToast.mockClear()
        vi.spyOn(console, "debug").mockReturnValue(undefined)
    })

    it("shows an info toast for Quasar Notify's 5 seconds", () => {
        notify("Saved")

        expect(addToast).toHaveBeenCalledWith("Saved", { variant: "info", duration: 5000 })
    })

    it("keeps an error toast up long enough to read the server message", () => {
        notifyOnCatch(new Error("Repository metadata could not be reset"))

        expect(addToast).toHaveBeenCalledWith("Repository metadata could not be reset", {
            variant: "danger",
            duration: 10000,
        })
    })
})

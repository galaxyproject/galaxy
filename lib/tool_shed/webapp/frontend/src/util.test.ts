import { beforeEach, describe, expect, it, vi } from "vitest"

const addToast = vi.fn()
vi.mock("@galaxyproject/galaxy-ui", () => ({ useToast: () => ({ addToast }) }))

const { copyAndNotify, downloadTextFile, getCookie, notify, notifyOnCatch } = await import("./util")

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

describe("getCookie", () => {
    it("reads and decodes a cookie, and returns null for one that isn't set", () => {
        document.cookie = "other=1"
        document.cookie = `session_csrf_token=${encodeURIComponent("a b=c")}`

        expect(getCookie("session_csrf_token")).toBe("a b=c")
        expect(getCookie("missing")).toBeNull()
    })

    it("returns a value that isn't valid percent-encoding as is", () => {
        document.cookie = "broken=100%"

        expect(getCookie("broken")).toBe("100%")
    })
})

describe("copyAndNotify", () => {
    beforeEach(() => {
        addToast.mockClear()
    })

    it("copies through the Clipboard API and confirms", async () => {
        const writeText = vi.fn().mockResolvedValue(undefined)
        vi.stubGlobal("navigator", { clipboard: { writeText } })
        vi.stubGlobal("isSecureContext", true)

        await copyAndNotify("tsadminkey", "API key copied to your clipboard")

        expect(writeText).toHaveBeenCalledWith("tsadminkey")
        expect(addToast).toHaveBeenCalledWith(
            "API key copied to your clipboard",
            expect.objectContaining({ variant: "info" }),
        )
        vi.unstubAllGlobals()
    })

    it("reports a refused copy instead of confirming it", async () => {
        vi.stubGlobal("navigator", { clipboard: { writeText: vi.fn().mockRejectedValue(new Error("denied")) } })
        vi.stubGlobal("isSecureContext", true)

        await copyAndNotify("tsadminkey", "API key copied to your clipboard")

        expect(addToast).toHaveBeenCalledWith(
            "Your browser did not allow copying to the clipboard.",
            expect.objectContaining({ variant: "danger" }),
        )
        vi.unstubAllGlobals()
    })
})

describe("downloadTextFile", () => {
    it("downloads the contents under the given file name", () => {
        const createObjectURL = vi.fn().mockReturnValue("blob:contents")
        const revokeObjectURL = vi.fn()
        vi.stubGlobal("URL", { ...URL, createObjectURL, revokeObjectURL })
        const clicked: HTMLAnchorElement[] = []
        const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (
            this: HTMLAnchorElement,
        ) {
            clicked.push(this)
        })

        vi.useFakeTimers()

        downloadTextFile("tool_dependencies.xml", "<tool_dependency />")

        expect(clicked).toHaveLength(1)
        expect(clicked[0].download).toBe("tool_dependencies.xml")
        expect(clicked[0].href).toBe("blob:contents")
        // Revoked only after the browser has had time to read the blob
        expect(revokeObjectURL).not.toHaveBeenCalled()
        vi.advanceTimersByTime(10000)
        expect(revokeObjectURL).toHaveBeenCalledWith("blob:contents")
        vi.useRealTimers()
        click.mockRestore()
        vi.unstubAllGlobals()
    })
})

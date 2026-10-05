import { useToast, type ToastVariant } from "@galaxyproject/galaxy-ui"
import { type LocationQueryValue } from "vue-router"
import { type ApiMessageException } from "./schema/types"

export function getCookie(name: string): string | null {
    const prefix = `${encodeURIComponent(name)}=`
    const cookie = document.cookie.split("; ").find((part) => part.startsWith(prefix))
    if (cookie === undefined) {
        return null
    }
    const value = cookie.slice(prefix.length)
    try {
        return decodeURIComponent(value)
    } catch {
        // A value that isn't valid percent-encoding is still the cookie's value
        return value
    }
}

export function ensureCookie(name: string): string {
    const cookie = getCookie(name)
    if (cookie == null) {
        notify(
            "An important cookie was not set by the tool shed server, this may result in serious problems.",
            "warning",
        )
        throw Error(`Cookie ${name} not set`)
    }
    return cookie
}

const { addToast } = useToast()

// Quasar Notify's 5s, with errors held longer so a server message can be read in full
const NOTIFY_DURATION = 5000
const ERROR_NOTIFY_DURATION = 10000

export function notify(notification: string, variant: ToastVariant = "info") {
    addToast(notification, { variant, duration: variant === "danger" ? ERROR_NOTIFY_DURATION : NOTIFY_DURATION })
}

async function writeToClipboard(value: string) {
    if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(value)
        return
    }
    // The Clipboard API needs a secure context; plain-http deployments fall back to the old copy command
    // Focused and editable, as older and mobile Safari only copy from an active editable field
    const textarea = document.createElement("textarea")
    textarea.value = value
    textarea.contentEditable = "true"
    textarea.style.position = "fixed"
    textarea.style.opacity = "0"
    document.body.appendChild(textarea)
    textarea.focus()
    textarea.select()
    const copied = document.execCommand("copy")
    textarea.remove()
    if (!copied) {
        throw new Error("Copy command was refused")
    }
}

export async function copyAndNotify(value: string, notification: string) {
    try {
        await writeToClipboard(value)
        notify(notification)
    } catch (e) {
        notify("Your browser did not allow copying to the clipboard.", "danger")
    }
}

export function downloadTextFile(fileName: string, contents: string) {
    const url = URL.createObjectURL(new Blob([contents], { type: "text/plain" }))
    const link = document.createElement("a")
    link.href = url
    link.download = fileName
    document.body.appendChild(link)
    link.click()
    link.remove()
    // Safari can still be reading the blob after click() returns, so let it go later
    setTimeout(() => URL.revokeObjectURL(url), 10000)
}

export function errorMessageAsString(
    e: Error | ApiMessageException | string | unknown,
    defaultMessage = "Request failed.",
): string {
    if (e instanceof Error) {
        if (e.cause) {
            return `${e.message}: ${e.cause}`
        }
        return e.message
    } else if (isApiException(e)) {
        return e.err_msg
    } else if (typeof e == "string") {
        return e
    }

    return defaultMessage
}

function isApiException(e: unknown): e is ApiMessageException {
    return e instanceof Object && "err_msg" in e
}

export function queryParamToString(param: LocationQueryValue | LocationQueryValue[]): string | null {
    return Array.isArray(param) ? param[0] : param
}

export function notifyOnCatch(e: unknown) {
    console.debug(e)
    notify(errorMessageAsString(e), "danger")
}

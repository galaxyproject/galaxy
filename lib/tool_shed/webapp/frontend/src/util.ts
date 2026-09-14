import { useToast, type ToastVariant } from "@galaxyproject/galaxy-ui"
import { copyToClipboard, Cookies } from "quasar"
import { type LocationQueryValue } from "vue-router"
import { type ApiMessageException } from "./schema/types"

export function getCookie(name: string): string | null {
    return Cookies.get(name)
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

export async function copyAndNotify(value: string, notification: string) {
    await copyToClipboard(value)
    notify(notification)
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

import { copyToClipboard, Notify, Cookies } from "quasar"
import type { QNotifyCreateOptions } from "quasar"
import { type LocationQueryValue } from "vue-router"
import { type ApiMessageException } from "./schema/types"

export function getCookie(name: string): string | null {
    return Cookies.get(name)
}

export function ensureCookie(name: string): string {
    const cookie = getCookie(name)
    if (cookie == null) {
        notify("An important cookie was not set by the tool shed server, this may result in serious problems.")
        throw Error(`Cookie ${name} not set`)
    }
    return cookie
}

export function notify(notification: string, type: string | null = null) {
    const opts: QNotifyCreateOptions = {
        message: notification,
    }
    if (type) {
        opts.type = type
    }
    Notify.create(opts)
}

export async function copyAndNotify(value: string, notification: string) {
    await copyToClipboard(value)
    notify(notification)
}

export function errorMessageAsString(
    e: Error | ApiMessageException | string | unknown,
    defaultMessage = "Request failed."
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
    notify(errorMessageAsString(e))
}

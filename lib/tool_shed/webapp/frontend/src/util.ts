import { copyToClipboard, Notify, Cookies } from "quasar"
import type { QNotifyCreateOptions } from "quasar"
import { type LocationQueryValue } from "vue-router"
import { ApiError } from "openapi-typescript-fetch"

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

export function errorMessage(e: Error): string {
    if (e instanceof ApiError) {
        return e.data.err_msg
    } else {
        return JSON.stringify(e)
    }
}

export function queryParamToString(param: LocationQueryValue | LocationQueryValue[]): string | null {
    return Array.isArray(param) ? param[0] : param
}

export function notifyOnCatch(e: Error) {
    notify(errorMessage(e))
}

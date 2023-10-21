import axios from "axios"
import { RawAxiosRequestConfig } from "axios"
import { components } from "@/schema"

type User = components["schemas"]["UserV2"]

export async function getCurrentUser(): Promise<User | null> {
    const conf: RawAxiosRequestConfig<unknown> = {}
    conf.validateStatus = (status: number) => {
        const valid = status == 200 || status == 404
        return valid
    }
    const { data: user, status } = await axios.get<object>("/api/users/current", conf)
    if (status == 404) {
        return null
    } else {
        return user as User
    }
}

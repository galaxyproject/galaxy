// https://www.vuemastery.com/blog/vue-3-data-down-events-up/
import { computed, WritableComputedRef } from "vue"

export function useModelWrapper<TProps, TKey extends keyof TProps>(
    props: TProps,
    emit: (event: string, value: TProps[TKey]) => void,
    name: TKey = "modelValue" as TKey
): WritableComputedRef<TProps[TKey]> {
    return computed<TProps[TKey]>({
        get: () => props[name],
        set: (value: TProps[TKey]) => {
            emit("update:modelValue", value)
        },
    })
}

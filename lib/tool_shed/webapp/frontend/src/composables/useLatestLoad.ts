import { ref, shallowRef, watch, type Ref, type WatchSource } from "vue"
import { errorMessageAsString } from "@/util"

export interface LatestLoad<T> {
    data: Ref<T | null>
    loading: Ref<boolean>
    error: Ref<string | null>
}

/**
 * Load whatever `source` names, keeping only the result for its latest value.
 * A null source clears the state without loading.
 */
export function useLatestLoad<S, T>(
    source: WatchSource<S | null>,
    load: (value: S) => Promise<T>,
    describeError: (e: unknown) => string = errorMessageAsString,
): LatestLoad<T> {
    const data = shallowRef<T | null>(null)
    const loading = ref(false)
    const error = ref<string | null>(null)
    watch(
        source,
        async (value, _previous, onCleanup) => {
            let stale = false
            onCleanup(() => {
                stale = true
            })
            data.value = null
            error.value = null
            loading.value = value !== null
            if (value === null) {
                return
            }
            try {
                const result = await load(value)
                if (!stale) {
                    data.value = result
                }
            } catch (e) {
                if (!stale) {
                    error.value = describeError(e)
                }
            } finally {
                if (!stale) {
                    loading.value = false
                }
            }
        },
        { immediate: true },
    )
    return { data, loading, error }
}

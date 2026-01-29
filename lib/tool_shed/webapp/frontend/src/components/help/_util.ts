import { computed } from "vue"

export const size = "64px"

export interface CommonProps {
    hAlign: "left" | "center"
    wrapperClass?: string
}

export function useCommonProps(props: CommonProps) {
    const classes = computed(() => {
        return [`text-${props.hAlign}`, "q-mt-md", props.hAlign == "left" ? "q-pb-xl" : null]
    })
    return { classes, size }
}

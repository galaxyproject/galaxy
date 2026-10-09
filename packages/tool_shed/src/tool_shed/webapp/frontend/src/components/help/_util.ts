import { computed } from "vue"

export const size = "64px"

export interface CommonProps {
    hAlign: "left" | "center"
    wrapperClass?: string
}

export function useCommonProps(props: CommonProps) {
    const classes = computed(() => [`help-align-${props.hAlign}`])
    return { classes, size }
}

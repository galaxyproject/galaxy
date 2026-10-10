import { defineComponent, h } from "vue"

export const MetadataJsonViewerStub = defineComponent({
    name: "MetadataJsonViewer",
    props: {
        data: { type: Object, required: true },
        modelName: { type: String, default: "" },
        deep: { type: Number, default: 0 },
    },
    setup(props) {
        return () => h("div", { class: "mock-json-viewer" }, JSON.stringify(props.data))
    },
})

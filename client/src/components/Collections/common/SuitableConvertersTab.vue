<template>
    <div>
        <div>
            <span class="float-left h-sm">将所有数据集转换为新格式</span>
            <div class="text-right">
                <button
                    class="run-tool-collection-edit btn btn-primary"
                    :disabled="selectedConverter == {}"
                    @click="clickedConvert">
                    {{ l("转换集合") }}
                </button>
            </div>
        </div>
        <b>{{ l("转换工具：") }}</b>
        <Multiselect
            v-model="selectedConverter"
            deselect-label="无法移除此值"
            track-by="name"
            label="name"
            :options="suitableConverters"
            :searchable="true"
            :allow-empty="true">
        </Multiselect>
    </div>
</template>

<script>
import Multiselect from "vue-multiselect";

export default {
    components: { Multiselect },
    props: {
        suitableConverters: {
            type: Array,
            required: true,
        },
    },
    data: function () {
        return {
            selectedConverter: {},
        };
    },
    methods: {
        clickedConvert: function () {
            this.$emit("clicked-convert", this.selectedConverter);
            this.selectedConverter = {};
        },
    },
};
</script>

<template>
    <div>
        <li class="dataset paired">
            <span class="forward-dataset-name flex-column">{{ pair.forward.name }}</span>
            <span class="pair-name-column flex-column">
                <span class="pair-name">
                    <click-to-edit v-model="name" :title="titlePairName" />
                </span>
            </span>
            <span class="reverse-dataset-name flex-column">{{ pair.reverse.name }}</span>
        </li>
        <button class="unpair-btn" @click="unlinkFn">
            <span class="fa fa-unlink" :title="unpairButtonTitle"></span>
        </button>
    </div>
</template>
<script>
import ClickToEdit from "./common/ClickToEdit.vue";
import _l from "utils/localization";
export default {
    components: { ClickToEdit },
    props: {
        pair: {
            required: true,
        },
        unlinkFn: {
            required: true,
            type: Function,
        },
    },
    data: function () {
        return {
            unpairButtonTitle: _l("Unpair"),
            titlePairName: _l("Click to rename"),
            name: "",
        };
    },
    watch: {
        pair() {
            this.name = this.pair.name;
        },
        name() {
            this.$emit("onPairRename", this.name);
        },
    },
    created: function () {
        this.name = this.pair.name;
    },
    methods: {
        l(str) {
            // _l conflicts private methods of Vue internals, expose as l instead
            return _l(str);
        },
    },
};
</script>

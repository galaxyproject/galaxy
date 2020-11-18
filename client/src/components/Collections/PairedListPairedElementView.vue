<template>
    <li>
        <span class="forward-dataset-name flex-column">{{ pair.forward.name }}</span>
        <span class="pair-name-column flex-column">
            <span class="pair-name">
                <click-to-edit :element="pair.name" />
            </span>
        </span>
        <span class="reverse-dataset-name flex-column">{{ pair.reverse.name }}</span>
    </li>
</template>
<script>
import ClickToEdit from "./common/ClickToEdit.vue";
export default {
    components: { ClickToEdit },
    data: function () {
        return {
            name: "",
        };
    },
    computed: {
        pairName: {
            get() {
                return this.name;
            },
            set(newName) {
                this.name = newName;
                this.$emit("pair-name-changed", this.name);
            },
        },
    },
    props: {
        pair: {
            required: true,
        },
    },
    methods: {},
};
</script>

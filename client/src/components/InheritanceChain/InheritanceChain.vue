<template>
    <div>
        <Heading id="inheritance-chain-heading" h1 separator inline size="md"> Inheritance Chain </Heading>
        <div class="current-dataset chain-box">{{ datasetName }}</div>
        <div v-if="inherit_chain && inherit_chain.length > 0">
            <div v-for="({ name, dep }, i) in inherit_chain" :key="i">
                <FontAwesomeIcon class="inheritance-arrow" size="3x" :icon="faLongArrowAltUp" />
                <div class="chain-box">{{ name }} in {{ dep }}</div>
            </div>
        </div>
    </div>
</template>

<script>
import { faLongArrowAltUp } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

import { Services } from "./services";

import Heading from "../Common/Heading.vue";

export default {
    components: { FontAwesomeIcon, Heading },
    props: {
        datasetName: {
            type: String,
            required: true,
        },
        datasetId: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            inherit_chain: [],
            faLongArrowAltUp,
        };
    },
    created() {
        this.services = new Services();
        this.services.getInheritanceChain(this.datasetId).then((result) => {
            this.inherit_chain = result;
        });
    },
};
</script>

<style scoped>
.chain-box {
    border: 1px solid #bbb;
    margin: 2% 2%;
    text-align: center;
    padding: 15px;
    background-color: #eee;
}
.current-dataset {
    background-color: #fff;
    font-weight: bold;
}
.inheritance-arrow {
    margin-left: 50%;
}
</style>

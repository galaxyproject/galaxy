<template>
    <div>
        <h3>Inheritance Chain</h3>
        <div class="current-dataset chain-box">{{ datasetName }}</div>
        <div v-if="inherit_chain && inherit_chain.length > 0">
            <div v-for="({ name, dep }, i) in inherit_chain" :key="i">
                <font-awesome-icon class="inheritance-arrow" size="3x" :icon="['fas', 'long-arrow-alt-up']" />
                <div class="chain-box">{{ name }} in {{ dep }}</div>
            </div>
        </div>
    </div>
</template>

<script>
import { Services } from "./services";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faLongArrowAltUp } from "@fortawesome/free-solid-svg-icons";

library.add(faLongArrowAltUp);

export default {
    components: { FontAwesomeIcon },
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

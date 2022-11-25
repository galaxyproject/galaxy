<template>
    <FontAwesomeIcon class="fa-code" :title="asJson" />
</template>

<script>
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCode } from "@fortawesome/free-solid-svg-icons";

library.add(faCode);

export default {
    components: { FontAwesomeIcon },
    props: {
        object: {
            type: Object,
            required: true,
        },
    },
    computed: {
        asJson: function () {
            return JSON.stringify(this.object);
        },
    },
};
</script>

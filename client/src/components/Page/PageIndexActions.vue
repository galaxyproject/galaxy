<template>
    <span>
        <b-button id="page-create" class="m-1" @click="create">
            <font-awesome-icon icon="plus" />
            {{ "Create" | localize }}
        </b-button>
    </span>
</template>

<script>
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";

import { faPlus } from "@fortawesome/free-solid-svg-icons";
import { library } from "@fortawesome/fontawesome-svg-core";
library.add(faPlus);

export default {
    components: {
        BButton,
        FontAwesomeIcon,
    },
    props: {
        root: {
            type: String,
            required: true,
        },
    },
    methods: {
        create: function () {
            window.location.assign(`${this.root}pages/create`);
        },
    },
};
</script>

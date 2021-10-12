<template>
    <b-breadcrumb>
        <b-breadcrumb-item>
            <b-dropdown class="justify-content-md-center">
                <template v-slot:button-content>
                    <font-awesome-icon icon="plug" />
                    {{ currentSource ? currentSource.doc : "Choose your remote" }}
                </template>
                <b-dropdown-item
                    @click="currentSource = fileSource"
                    v-for="(fileSource, index) in remoteFileSources"
                    :key="index"
                    >{{ fileSource.doc }}</b-dropdown-item
                >
            </b-dropdown>
        </b-breadcrumb-item>
        <b-breadcrumb-item class="d-flex align-items-center"> TEXT </b-breadcrumb-item>
        <b-breadcrumb-item class="directory-input-field">
            <b-form-input v-on:keyup.enter="addPath" v-model="directoryName" placeholder="Name your directory..." />
        </b-breadcrumb-item>
    </b-breadcrumb>
</template>

<script>
import { library } from "@fortawesome/fontawesome-svg-core";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faPlug } from "@fortawesome/free-solid-svg-icons";
import { Services } from "./services";

library.add(faPlug);

export default {
    components: {
        FontAwesomeIcon,
    },
    data() {
        return {
            remoteFileSources: [],
            currentSource: undefined,
            directoryName: "",
        };
    },
    created() {
        new Services().getFileSources().then((items) => {
            this.remoteFileSources = items;
        });
    },
    props: {
        callback: {
            type: Function,
            default: () => {},
        },
        title: {
            type: String,
            default: "copy to clipboard",
            required: false,
        },
    },methods:{
      addPath(){
        this.remoteFileSources.push(this.currentSource)
      }
  }
};
</script>

<style scoped>
.breadcrumb-item::before {
    font-size: 1.5rem;
}
.directory-input-field a {
    text-decoration: none;
}
</style>

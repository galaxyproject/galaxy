<template>
    <div>
        <FormCard title="Create a new Page" icon="fa-file-contract">
            <template v-slot:body>
                <div v-localize class="font-weight-bold py-2">Name</div>
                <FormInput v-model="name" />
                <div v-localize class="font-weight-bold py-2">Identifier</div>
                <FormInput v-model="identifier" />
                <small v-localize class="text-muted py-2">
                    A unique identifier that will be used for public links to this page. This field can only contain
                    lowercase letters, numbers, and dashes (-).
                </small>
                <div v-localize class="font-weight-bold py-2">Annotation</div>
                <FormInput v-model="annotation" />
                <small v-localize class="text-muted py-2">
                    A description of the page. The annotation is shown alongside published pages.
                </small>
            </template>
        </FormCard>
        <BButton variant="primary" v-localize>
            <FontAwesomeIcon :icon="faSave" class="mr-1"/>
            <span>Create</span>
        </BButton>
    </div>
</template>

<script setup>
import { ref } from "vue";
import { BButton } from "bootstrap-vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faSave } from "@fortawesome/free-solid-svg-icons";

import FormCard from "@/components/Form/FormCard";
import FormInput from "@/components/Form/Elements/FormInput.vue";

const annotation = ref("");
const identifier = ref("");
const name = ref("");
</script>

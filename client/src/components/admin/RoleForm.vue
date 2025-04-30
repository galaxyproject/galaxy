<template>
    <div>
        <LoadingSpan v-if="loading" />
        <div v-else>
            <BAlert v-if="errorMessage" variant="danger" show>{{ errorMessage }}</BAlert>
            <FormCard title="Create a new Role" icon="fa-file-contract">
                <template v-slot:body>
                    <FormElementLabel title="Title" :required="true" :condition="!!name">
                        <FormInput id="role-name" v-model="name" />
                    </FormElementLabel>
                </template>
            </FormCard>
            <BButton id="role-submit" class="my-2" variant="primary" @click="onSubmit">
                <FontAwesomeIcon :icon="faSave" class="mr-1" />
                <span v-localize>Create</span>
            </BButton>
        </div>
    </div>
</template>

<script setup lang="ts">
import { faSave } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton } from "bootstrap-vue";
import { ref } from "vue";
import { useRouter } from "vue-router/composables";

import { GalaxyApi } from "@/api";

import FormInput from "@/components/Form/Elements/FormInput.vue";
import FormCard from "@/components/Form/FormCard.vue";
import FormElementLabel from "@/components/Form/FormElementLabel.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const errorMessage = ref("");
const loading = ref(false);
const name = ref("");

const router = useRouter();

async function fetchData() {
    loading.value = true;
    const { data: groups, error: groupsError } = await GalaxyApi().GET("/api/groups");
    if (groupsError) {
        errorMessage.value = groupsError.err_msg;
    } else {
        const { data: roles, error: rolesError } = await GalaxyApi().GET("/api/roles");
        if (rolesError) {
            errorMessage.value = rolesError.err_msg;
        } else {
            errorMessage.value = "";
            
        }
    }
    loading.value = false;
}

async function onSubmit() {
    if (false) {
        errorMessage.value = "Please complete all required inputs.";
        return;
    }

    /*const { data, error } = await GalaxyApi().POST("/api/roles", {
        body: {
            name: name.value,
        },
    });
    if (error) {
        errorMessage.value = error.err_msg;
    } else {
        router.push("/admin/roles");
    }*/ 
}

fetchData();
</script>

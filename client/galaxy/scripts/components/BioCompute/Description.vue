<template>
    <div id="description">
        <div v-show="bco" class="bco-stats">
            <h2 class="domain">Description Domain</h2>
            <tr><h3>Key Words</h3></tr>
            <span v-for="object in bco.description_domain.keywords" :key="object">
                <tr>
                    <td> <textarea v-model="object" /> </td>
                </tr>
            </span>
            <tr>
                <td>Platform:</td><td></td> 
            </tr>
        </div>
    </div>
</template>

<script>
export default {
    name: "description",
    props: ["bco"],
};
</script>

<template>
    <div id="top-level">
        <div v-show="bco">
            <h2 class="domain">Top Level</h2>
            <tr>
                <td>BioCompute ID:</td>
                <td>{{ bco.object_id }}</td>
            </tr>
            <tr>
                <td>E-Tag</td>
                <td>{{ bco.etag }}</td>
            </tr>
            <tr>
                <td>Spec Version</td>
                <td>{{ bco.spec_version }}</td>
                <td><button>Edit</button></td>
            </tr>
        </div>
    </div>
</template>

<script>
export default {
    name: "top-level",
    props: ["bco"],
};
</script>

<style></style>

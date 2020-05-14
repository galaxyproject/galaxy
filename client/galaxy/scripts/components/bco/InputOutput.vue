<template>
    <div id="inputoutput">
        <div v-show="bco">
            <h2 class="domain">Input/Output Domain</h2>
            <table v-for="object in bco.io_domain" :key="object">
                <tr>
                    {{
                        object
                    }}
                </tr>
                <td><button>Edit</button></td>
            </table>
        </div>
    </div>
</template>

<script>
export default {
    name: "inputoutput",
    props: ["bco"],
};
</script>

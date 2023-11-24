<script setup lang="ts">
import ExternalLink from "@/components/ExternalLink.vue";
import Heading from "@/components/Common/Heading.vue";
import Abbreviation from "@/components/Common/Abbreviation.vue";

const dictionary = [
    {
        term: "TDP (Thermal Design Power)",
        definition: "The maximum amount of heat a CPU can produce in Watts. This correlates with power usage.",
    },
    {
        term: "PUE (Power Usage Effectiveness)",
        definition: "A measure of how of much energy a data center running your server uses.",
    },
    {
        term: "Carbon Intensity",
        definition: "The amount greenhouse gases emitted per unit of electricity produced.",
    },
    {
        term: "AWS EC2",
        definition: "An Amazon service allowing users to rent virtual computers and deploy their own web services.",
    },
    {
        term: "CO2e",
        definition:
            "Other types of greenhouse gases that have similar global warming potential as a metric unit amount of CO2 itself.",
    },
];

const epaUrl = "https://www.epa.gov/energy/greenhouse-gas-equivalencies-calculator";
const epaCalculationsUrl =
    "https://www.epa.gov/energy/greenhouse-gases-equivalencies-calculator-calculations-and-references";
const greenAlgorithmsUrl = "https://www.green-algorithms.org/";
</script>

<template>
    <article class="mt-4">
        <header>
            <Heading h1 separator bold size="lg">Carbon Emissions Calculations</Heading>

            <p>
                Our calculations are based off of the work of the
                <ExternalLink :href="greenAlgorithmsUrl">Green Algorithms Project</ExternalLink>
                and in particular their implementation of the "carbon footprint calculator".

                <br />

                Additionally, some of our carbon emissions comparisons are based off of calculations done by the
                <ExternalLink :href="epaUrl">United States Environmental Protection Agency (EPA)</ExternalLink>.
            </p>
        </header>

        <section>
            <Heading h2 separator bold size="sm">How we calculate carbon emissions</Heading>

            <p>
                For each job, the carbon emissions are based off of the job runtime (in hours) and the memory allocated
                to it (in MB). Additionally, we require information about the CPU model of the server that ran the job.
                In particular, we consider the CPU
                <Abbreviation :explanation="'Thermal Design Power'">TDP</Abbreviation>, its core count and the number of
                those cores allocated to the job. We assume a real core usage factor of 1.0, meaning that that 100% of
                each allocated core's resources are used. Given that CPU specifications can vary greatly and that we
                cannot always assume this information is provided, we have two approaches:
            </p>

            <ol>
                <li>In the case that the server's CPU specifications are known, we proceed as normal.</li>
                <li>
                    When no information is provided, we estimate the server's configuration by matching your job's CPU
                    and/or memory usage to a comparable general purpose
                    <Abbreviation :explanation="'Amazon Web Services Elastic Compute Cloud'">AWS EC2</Abbreviation>
                    instance. EC2 was chosen because its service provides numerous server configurations allowing us to
                    cover more real-world situations.
                    <ExternalLink :href="'https://aws.amazon.com/ec2/instance-types/'">
                        (Click here to read further about general purpose EC2 machines)
                    </ExternalLink>
                </li>
            </ol>

            <p>
                Once we have the information needed, we calculate the power usage of the CPU and memory in watts. For
                each component, the respective power usage is the product of the amount of allocated resources, a
                <Abbreviation :explanation="'Power Usage Effectiveness'">PUE</Abbreviation> value and a power usage
                factor. For CPUs power usage factor is the TDP (normalized to TDP-per-core) and for memory we use an
                average memory power draw constant of 0.375 W/GiB.
            </p>

            <pre>
                memory_allocated_in_gibibyte = memory_allocated_in_mebibyte / 1024
                tdp_per_core = cpu_TDP / cpu_core_count
                normalized_tdp_per_core = tdp_per_core * cores_allocated_to_job

                power_needed_cpu = pue * normalized_tdp_per_core
                power_needed_memory = pue * memory_allocated_in_gibibyte * memory_power_usage_constant
                total_power_needed = power_needed_cpu + power_needed_memory
            </pre>

            <p>
                The power usage is then converted into energy usage (in kWh) by factoring in the job runtime (in hours):
            </p>

            <pre>
                energy_needed_cpu = runtime * power_needed_cpu / 1000
                energy_needed_memory = runtime * power_needed_memory / 1000
                total_energy_needed = runtime * total_power_needed / 1000
            </pre>

            <p>
                Finally, we convert the energy usage into estimated carbon emissions (in metric units CO2e) by
                multiplying the carbon intensity of the server location:
            </p>

            <pre>
                cpu_carbon_emissions = energy_needed_cpu * carbon_intensity
                memory_carbon_emissions = energy_needed_memory * carbon_intensity
                total_carbon_emissions = total_energy_needed * carbon_intensity
            </pre>
        </section>

        <section>
            <Heading h2 separator bold size="sm">How we compare carbon emissions</Heading>

            <p>
                We compare the total carbon emissions of your job (per metric unit of CO2e) with
                <ExternalLink :href="epaCalculationsUrl">carbon emission estimates calculated by the EPA</ExternalLink>.
                When calculating the equivalent distance driven, we use the same reference values from the Green
                Algorithms Project's "Carbon emissions Calculator" tool.
            </p>

            <pre>
                gasoline_consumed = total_carbon_emissions / gasoline_emissions_as_per_epa
                carbon_carbon_savings_by_using_leds = total_carbon_emissions / led_carbon_savings_as_per_epa
                equivalent_km_in_eu = total_carbon_emissions / average_passenger_car_emissions_eu
                equivalent_km_in_us = total_carbon_emissions / average_passenger_car_emissions_us
                smartphones_charged = total_carbon_emissions / smartphone_charged_emissions_as_per_epa
                tree_months = total_carbon_emissions / tree_year * 12
            </pre>
        </section>

        <footer class="py-4">
            <Heading h2 separator bold size="sm">Glossary</Heading>

            <table class="tabletip info_data_table">
                <thead>
                    <th>Term</th>
                    <th>Definition</th>
                </thead>

                <tbody>
                    <tr v-for="{ term, definition } in dictionary" :key="term">
                        <td>{{ term }}</td>
                        <td>{{ definition }}</td>
                    </tr>
                </tbody>
            </table>
        </footer>
    </article>
</template>

<style lang="scss" scoped>
@import "scss/theme/blue.scss";

pre {
    font-weight: bold;
    white-space: pre-line;
    line-height: 1.5rem;
    background-color: $gray-100;
    border: 1px solid $brand-secondary;
    border-radius: 4px;
    padding: 1rem;
}

section {
    margin-top: 4rem;
}
</style>

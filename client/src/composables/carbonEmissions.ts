import { computed } from "vue";

import { worldwideCarbonIntensity } from "@/components/CarbonEmissions/carbonEmissionConstants";

import { useConfig } from "./config";

export function useCarbonEmissions() {
    const { config } = useConfig(true);
    const carbonIntensity = computed(() => (config.value?.carbon_intensity as number) ?? worldwideCarbonIntensity);
    const geographicalServerLocationName = computed(
        () => (config.value?.geographical_server_location_name as string) ?? "GLOBAL"
    );

    return {
        carbonIntensity,
        geographicalServerLocationName,
    };
}

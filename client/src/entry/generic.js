import { initGalaxyInstance } from "@/app";
import { onDomReady } from "@/utils/onDomReady";

onDomReady(async () => {
    await initGalaxyInstance();
});

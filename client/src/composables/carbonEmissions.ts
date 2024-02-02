export type EstimatedServerInstance = {
    name: string;
    cpuInfo: {
        modelName: string;
        totalAvailableCores: number;
        tdp: number;
    };
};

export async function estimateServerInstance(allocatedCores?: number, allocatedMemory?: number) {
    if (!allocatedCores) {
        return;
    }

    const adjustedMemory = allocatedMemory ? allocatedMemory / 1024 : 0;

    const ec2 = (await import("@/components/JobMetrics/awsEc2ReferenceData.js")).ec2Instances;
    if (!ec2) {
        return;
    }

    const serverInstance = ec2.find((instance) => {
        if (adjustedMemory === 0) {
            // Exclude memory from search criteria
            return instance.vCpuCount >= allocatedCores;
        }

        // Search by all criteria
        return instance.mem >= adjustedMemory && instance.vCpuCount >= allocatedCores;
    });

    if (!serverInstance) {
        return;
    }

    const cpu = serverInstance.cpu[0];
    if (!cpu) {
        return;
    }

    return {
        name: serverInstance.name,
        cpuInfo: {
            modelName: cpu.cpuModel,
            totalAvailableCores: cpu.coreCount,
            tdp: cpu.tdp,
        },
    };
}

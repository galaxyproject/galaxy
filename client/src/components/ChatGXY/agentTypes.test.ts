import {
    faBug,
    faChartBar,
    faGraduationCap,
    faMagic,
    faPlus,
    faRobot,
    faRoute,
} from "@fortawesome/free-solid-svg-icons";
import { describe, expect, it } from "vitest";

import {
    agentIconMap,
    agentTypes,
    formatModelName,
    getAgentIcon,
    getAgentLabel,
    getAgentResponseOrEmpty,
} from "./agentTypes";

describe("agentTypes", () => {
    describe("agentTypes array", () => {
        it("contains all 6 agent types", () => {
            expect(agentTypes).toHaveLength(6);
        });

        it("has expected agent values", () => {
            const values = agentTypes.map((a) => a.value);
            expect(values).toEqual([
                "auto",
                "router",
                "error_analysis",
                "custom_tool",
                "dataset_analyzer",
                "gtn_training",
            ]);
        });

        it("each entry has label, icon, and description", () => {
            for (const agent of agentTypes) {
                expect(agent.label).toBeTruthy();
                expect(agent.icon).toBeDefined();
                expect(agent.description).toBeTruthy();
            }
        });
    });

    describe("agentIconMap", () => {
        it("maps known agent types to icons", () => {
            expect(agentIconMap["auto"]).toBe(faMagic);
            expect(agentIconMap["router"]).toBe(faRoute);
            expect(agentIconMap["error_analysis"]).toBe(faBug);
            expect(agentIconMap["custom_tool"]).toBe(faPlus);
            expect(agentIconMap["dataset_analyzer"]).toBe(faChartBar);
            expect(agentIconMap["gtn_training"]).toBe(faGraduationCap);
        });
    });

    describe("getAgentIcon", () => {
        it("returns correct icon for known agent types", () => {
            expect(getAgentIcon("auto")).toBe(faMagic);
            expect(getAgentIcon("error_analysis")).toBe(faBug);
        });

        it("returns faRobot for unknown agent type", () => {
            expect(getAgentIcon("nonexistent")).toBe(faRobot);
        });

        it("returns faRobot for undefined", () => {
            expect(getAgentIcon(undefined)).toBe(faRobot);
        });

        it("returns faRobot for empty string", () => {
            expect(getAgentIcon("")).toBe(faRobot);
        });
    });

    describe("getAgentLabel", () => {
        it("returns label for known agent types", () => {
            expect(getAgentLabel("auto")).toBe("Auto (Router)");
            expect(getAgentLabel("error_analysis")).toBe("Error Analysis");
            expect(getAgentLabel("gtn_training")).toBe("GTN Training");
        });

        it("returns raw value for unknown agent type", () => {
            expect(getAgentLabel("my_custom_agent")).toBe("my_custom_agent");
        });

        it("returns 'AI Assistant' for undefined", () => {
            expect(getAgentLabel(undefined)).toBe("AI Assistant");
        });

        it("returns 'AI Assistant' for empty string", () => {
            expect(getAgentLabel("")).toBe("AI Assistant");
        });
    });

    describe("formatModelName", () => {
        it("extracts last segment from slash-separated model name", () => {
            expect(formatModelName("openai/gpt-4")).toBe("gpt-4");
            expect(formatModelName("anthropic/claude-3-opus")).toBe("claude-3-opus");
        });

        it("returns model name as-is if no slashes", () => {
            expect(formatModelName("gpt-4")).toBe("gpt-4");
        });

        it("returns empty string for undefined", () => {
            expect(formatModelName(undefined)).toBe("");
        });

        it("returns empty string for empty string", () => {
            expect(formatModelName("")).toBe("");
        });

        it("handles trailing slash", () => {
            // "openai/".split("/") => ["openai", ""] => last is "" => fallback to original
            expect(formatModelName("openai/")).toBe("openai/");
        });
    });

    describe("getAgentResponseOrEmpty", () => {
        it("returns provided response when present", () => {
            const response = {
                content: "hello",
                agent_type: "auto",
                confidence: "high" as const,
                suggestions: [],
                metadata: { model: "gpt-4" },
            };
            expect(getAgentResponseOrEmpty(response)).toBe(response);
        });

        it("returns empty response for undefined", () => {
            const result = getAgentResponseOrEmpty(undefined);
            expect(result.content).toBe("");
            expect(result.agent_type).toBe("");
            expect(result.confidence).toBe("low");
            expect(result.suggestions).toEqual([]);
            expect(result.metadata).toEqual({});
        });
    });
});

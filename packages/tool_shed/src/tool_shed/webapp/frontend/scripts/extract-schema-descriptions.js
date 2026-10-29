#!/usr/bin/env node
/**
 * Extract field descriptions from the TypeScript schema for use in MetadataInspector.
 *
 * Parses schema.ts and extracts @description annotations from JSDoc comments.
 *
 * Usage: node scripts/extract-schema-descriptions.js
 */

const fs = require("fs")
const path = require("path")

// Models to extract descriptions from
const MODELS_TO_EXTRACT = [
    "RepositoryRevisionMetadata",
    "RepositoryTool",
    "RepositoryDependency",
    "Repository",
    "ChangesetMetadataStatus",
    "ResetMetadataOnRepositoryResponse",
    "RepositoryMetadata",
]

function extractDescriptions(schemaContent) {
    const descriptions = {}

    for (const modelName of MODELS_TO_EXTRACT) {
        descriptions[modelName] = {}

        // Find the model definition: "ModelName: {"
        const modelPattern = new RegExp(`${modelName}:\\s*\\{([\\s\\S]*?)\\n\\s{8}\\}`, "g")
        const modelMatch = modelPattern.exec(schemaContent)

        if (!modelMatch) {
            console.log(`  Model ${modelName} not found`)
            continue
        }

        const modelContent = modelMatch[1]

        // Extract fields with @description annotations
        // Pattern: /** ... @description ... */ fieldName: type
        const fieldPattern = /\/\*\*[\s\S]*?@description\s+([\s\S]*?)\*\/\s*(\w+):/g
        let fieldMatch

        while ((fieldMatch = fieldPattern.exec(modelContent)) !== null) {
            const description = fieldMatch[1]
                .replace(/\s*\*\s*/g, " ") // Remove JSDoc asterisks
                .replace(/\s+/g, " ") // Normalize whitespace
                .trim()
            const fieldName = fieldMatch[2]

            if (description && fieldName) {
                descriptions[modelName][fieldName] = description
            }
        }

        // Also extract simple /** Field Name */ comments as fallback descriptions
        // Only if we didn't get a @description for that field
        const simplePattern = /\/\*\*\s*([^@*]+?)\s*\*\/\s*(\w+):/g
        let simpleMatch

        while ((simpleMatch = simplePattern.exec(modelContent)) !== null) {
            const comment = simpleMatch[1].trim()
            const fieldName = simpleMatch[2]

            // Only use if no @description was found and comment looks useful
            if (!descriptions[modelName][fieldName] && comment && !comment.includes("@")) {
                // Convert "Field Name" style comments to sentence descriptions
                descriptions[modelName][fieldName] = comment
            }
        }

        const fieldCount = Object.keys(descriptions[modelName]).length
        console.log(`  ${modelName}: ${fieldCount} field(s)`)
    }

    return descriptions
}

// Main
const schemaPath = path.join(__dirname, "../src/schema/schema.ts")
const outputPath = path.join(__dirname, "../src/components/MetadataInspector/fieldDescriptions.json")

console.log("Extracting schema descriptions...")
console.log(`  Source: ${schemaPath}`)

const schemaContent = fs.readFileSync(schemaPath, "utf8")
const descriptions = extractDescriptions(schemaContent)

// Write output
fs.writeFileSync(outputPath, JSON.stringify(descriptions, null, 2))
console.log(`\nWritten to: ${outputPath}`)

// Summary
let totalFields = 0
for (const model of Object.values(descriptions)) {
    totalFields += Object.keys(model).length
}
console.log(`Total: ${totalFields} field descriptions extracted`)

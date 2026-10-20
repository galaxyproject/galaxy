interface ShedYmlRepository {
    name: string
    owner: string
    type: string
    description: string
    long_description?: string | null
    homepage_url?: string | null
    remote_repository_url?: string | null
}

// Left plain only when YAML would read it back as the same string, otherwise JSON's quoting is valid YAML.
// Starting with a letter rules out numbers, dates and indicators; booleans and null are the words left.
const PLAIN_SCALAR = /^[A-Za-z][\w ./()+,-]*$|^https?:\/\/[^\s#]+$/
const RESOLVES_TO_NON_STRING = /^(true|false|yes|no|on|off|y|n|null)$/i

function scalar(value: string): string {
    if (PLAIN_SCALAR.test(value) && !RESOLVES_TO_NON_STRING.test(value) && !value.endsWith(" ")) {
        return value
    }
    return JSON.stringify(value)
}

function block(value: string): string {
    if (!value.includes("\n") || /^\s/.test(value)) {
        return scalar(value)
    }
    const chomp = value.endsWith("\n") ? "|" : "|-"
    const lines = value.replace(/\n$/, "").split("\n")
    return `${chomp}\n${lines.map((line) => (line ? `  ${line}` : "")).join("\n")}`
}

// The .shed.yml planemo would create or update this repository from. Planemo never uploads the file
// itself, so it is rebuilt from the repository's settings.
export function shedYml(repository: ShedYmlRepository, categories: string[]): string {
    const lines = [
        `name: ${scalar(repository.name)}`,
        `owner: ${scalar(repository.owner)}`,
        `description: ${scalar(repository.description)}`,
    ]
    if (repository.long_description) {
        lines.push(`long_description: ${block(repository.long_description)}`)
    }
    if (repository.homepage_url) {
        lines.push(`homepage_url: ${scalar(repository.homepage_url)}`)
    }
    if (repository.remote_repository_url) {
        lines.push(`remote_repository_url: ${scalar(repository.remote_repository_url)}`)
    }
    lines.push(`type: ${scalar(repository.type)}`)
    if (categories.length > 0) {
        lines.push("categories:", ...categories.map((category) => `- ${scalar(category)}`))
    }
    return `${lines.join("\n")}\n`
}

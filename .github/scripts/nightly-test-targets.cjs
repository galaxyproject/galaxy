const fs = require("node:fs");

async function resolveTargets(github, targets) {
  const branches = new Set();
  const include = [];
  for (const target of targets) {
    if (
      !/^(dev|release_\d+\.\d+)$/.test(target.branch) ||
      branches.has(target.branch)
    ) {
      throw new Error(`Invalid or duplicate nightly branch: ${target.branch}`);
    }
    if (!/^3\.\d+$/.test(target.python)) {
      throw new Error(
        `Invalid Python version for ${target.branch}: ${target.python}`,
      );
    }
    branches.add(target.branch);
    const { data } = await github.rest.repos.getBranch({
      owner: "galaxyproject",
      repo: "galaxy",
      branch: target.branch,
    });
    include.push({
      ...target,
      sha: data.commit.sha,
      postgres: target.postgres || "18",
      postgres_driver: target.postgres_driver || "psycopg",
      framework_api: JSON.stringify(
        target.framework_api || ["never", "always"],
      ),
      toolshed_api: JSON.stringify(target.toolshed_api || ["v2"]),
    });
  }
  if (!include.length) {
    throw new Error("At least one nightly branch must be configured");
  }
  return { include };
}

module.exports = async ({ github, core }) => {
  const targets = JSON.parse(
    fs.readFileSync(".github/nightly-test-targets.json", "utf8"),
  );
  core.setOutput(
    "matrix",
    JSON.stringify(await resolveTargets(github, targets)),
  );
};
module.exports.resolveTargets = resolveTargets;

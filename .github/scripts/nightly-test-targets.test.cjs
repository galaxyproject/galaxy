const assert = require("node:assert/strict");
const test = require("node:test");
const { resolveTargets } = require("./nightly-test-targets.cjs");

function branchApi() {
  const calls = [];
  return {
    calls,
    rest: {
      repos: {
        getBranch: async (params) => {
          calls.push(params);
          return { data: { commit: { sha: `commit-${params.branch}` } } };
        },
      },
    },
  };
}

test("each branch gets its own version and resolved upstream commit", async () => {
  const api = branchApi();
  const { include } = await resolveTargets(api, [
    { branch: "dev", python: "3.10" },
    { branch: "release_26.2", python: "3.11" },
  ]);
  assert.deepEqual(
    include.map(({ branch, python, sha }) => ({ branch, python, sha })),
    [
      { branch: "dev", python: "3.10", sha: "commit-dev" },
      { branch: "release_26.2", python: "3.11", sha: "commit-release_26.2" },
    ],
  );
  assert.ok(
    api.calls.every(
      ({ owner, repo }) => owner === "galaxyproject" && repo === "galaxy",
    ),
  );
});

test("older release setup survives Python version changes", async () => {
  const { include } = await resolveTargets(branchApi(), [
    {
      branch: "release_26.0",
      python: "3.10",
      postgres: "17",
      postgres_driver: "psycopg2",
      framework_api: ["if_needed", "always"],
      toolshed_api: ["v1", "v2"],
    },
  ]);
  assert.equal(include[0].postgres, "17");
  assert.equal(include[0].postgres_driver, "psycopg2");
  assert.deepEqual(JSON.parse(include[0].framework_api), [
    "if_needed",
    "always",
  ]);
  assert.deepEqual(JSON.parse(include[0].toolshed_api), ["v1", "v2"]);
});

test("a missing branch fails preparation instead of silently dropping coverage", async () => {
  const api = branchApi();
  api.rest.repos.getBranch = async () => {
    throw new Error("not found");
  };
  await assert.rejects(
    resolveTargets(api, [{ branch: "release_26.2", python: "3.10" }]),
    /not found/,
  );
});

test("duplicate branches cannot run competing reporters", async () => {
  await assert.rejects(
    resolveTargets(branchApi(), [
      { branch: "dev", python: "3.10" },
      { branch: "dev", python: "3.14" },
    ]),
    /duplicate/,
  );
});

test("empty targets and malformed branch/version selections fail visibly", async () => {
  await assert.rejects(resolveTargets(branchApi(), []), /At least one/);
  await assert.rejects(
    resolveTargets(branchApi(), [{ branch: "feature", python: "3.10" }]),
    /Invalid/,
  );
  await assert.rejects(
    resolveTargets(branchApi(), [{ branch: "dev", python: "latest" }]),
    /Invalid Python/,
  );
});

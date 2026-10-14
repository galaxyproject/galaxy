import fs from "node:fs";
import assert from "node:assert/strict";
const yaml = fs.readFileSync(
  new URL("../workflows/_report_scheduled_result.yaml", import.meta.url),
  "utf8",
);
const script = yaml
  .split("script: |\n")[1]
  .split("\n")
  .map((l) => l.replace(/^ {12}/, ""))
  .join("\n");
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;
const fn = new AsyncFunction("github", "context", script);

async function run({
  needs,
  open = [],
  jobs = [],
  labels = "area/testing, kind/bug",
  issueTitle = "Scheduled unit tests are failing",
  testedSha = "",
  jobNamePrefix = "",
}) {
  const calls = [];
  const github = {
    paginate: async (method, params) => method(params),
    rest: {
      issues: {
        listForRepo: (p) => {
          calls.push(["list", p]);
          return open;
        },
        createComment: async (p) => calls.push(["comment", p]),
        create: async (p) => calls.push(["create", p]),
        update: async (p) => calls.push(["update", p]),
      },
      actions: {
        listJobsForWorkflowRunAttempt: (p) => {
          calls.push(["jobs", p]);
          return jobs;
        },
      },
    },
  };
  const context = {
    repo: { owner: "galaxyproject", repo: "galaxy" },
    serverUrl: "https://github.com",
    runId: 42,
    runAttempt: 2,
    sha: "abc123",
  };
  Object.assign(process.env, {
    TITLE: issueTitle,
    TESTED_SHA: testedSha,
    JOB_NAME_PREFIX: jobNamePrefix,
    LABELS: labels,
    DESCRIPTION: "Intro.\n\nMore.",
    NEEDS: JSON.stringify(needs),
  });
  await fn(github, context);
  return calls;
}
const title = "Scheduled unit tests are failing";
const jobs = [
  { name: "Test (3.10)", conclusion: "success" },
  { name: "Test (3.12)", conclusion: "failure" },
  { name: "Test (3.13)", conclusion: "timed_out" },
  { name: "report / Report scheduled result", conclusion: null },
];

// fail, none open -> create with labels, description, failed jobs
let c = await run({
  needs: { test: { result: "failure" } },
  jobs,
  open: [{ number: 9, title: "Other" }],
});
// lookup keys on title + creator only, so relabelling an open issue can't orphan it
assert.equal(c[0][1].labels, undefined);
assert.equal(c[0][1].state, "open");
assert.equal(c[0][1].creator, "github-actions[bot]");
assert.deepEqual(c[1][1], {
  owner: "galaxyproject",
  repo: "galaxy",
  run_id: 42,
  attempt_number: 2,
  per_page: 100,
});
assert.equal(c[2][0], "create");
assert.deepEqual(c[2][1].labels, ["area/testing", "kind/bug"]);
assert.equal(c[2][1].title, title);
assert.equal(
  c[2][1].body,
  "Intro.\n\nMore.\n\nFailed on abc123: https://github.com/galaxyproject/galaxy/actions/runs/42 (attempt 2)\n\nFailed jobs: Test (3.12), Test (3.13)\n\nLater failures are added as comments here; the next passing run closes this issue.",
);
assert.equal(c.length, 3);

// fail, one open -> comment on it
c = await run({
  needs: { test: { result: "failure" } },
  jobs,
  open: [{ number: 7, title }],
});
assert.deepEqual(
  c.map((x) => x[0]),
  ["list", "jobs", "comment"],
);
assert.equal(c[2][1].issue_number, 7);
assert.equal(
  c[2][1].body,
  "Still failing on abc123: https://github.com/galaxyproject/galaxy/actions/runs/42 (attempt 2)\n\nFailed jobs: Test (3.12), Test (3.13)",
);

// fail with no failed jobs listed (e.g. upstream skipped) -> no empty line
c = await run({
  needs: { "build-client": { result: "failure" }, test: { result: "skipped" } },
  jobs: [],
  open: [],
});
assert.equal(c[2][0], "create");
assert.ok(!c[2][1].body.includes("Failed jobs"));
assert.ok(!c[2][1].body.includes("\n\n\n"));

// skipped need alone counts as failure (matches old Selenium behaviour)
c = await run({
  needs: { "build-client": { result: "success" }, test: { result: "skipped" } },
  open: [],
});
assert.equal(c.at(-1)[0], "create");

// pass, two open -> comment + close both, no jobs query
c = await run({
  needs: { "build-client": { result: "success" }, test: { result: "success" } },
  open: [
    { number: 7, title },
    { number: 8, title },
    { number: 9, title: "Other" },
  ],
});
assert.deepEqual(
  c.map((x) => x[0]),
  ["list", "comment", "update", "comment", "update"],
);
assert.deepEqual(
  c
    .filter((x) => x[0] === "update")
    .map((x) => [x[1].issue_number, x[1].state, x[1].state_reason]),
  [
    [7, "closed", "completed"],
    [8, "closed", "completed"],
  ],
);

// pass, none open -> no-op
c = await run({ needs: { test: { result: "success" } }, open: [] });
assert.deepEqual(
  c.map((x) => x[0]),
  ["list"],
);

// label parsing tolerates spacing / trailing comma (selenium caller)
c = await run({
  needs: { test: { result: "failure" } },
  labels: "area/testing/selenium,kind/bug,",
  open: [],
});
assert.equal(c[0][1].labels, undefined);
assert.deepEqual(c.at(-1)[1].labels, ["area/testing/selenium", "kind/bug"]);
// A passing release cannot close a failing issue belonging to a different branch.
const devTitle = "Scheduled unit tests are failing (dev)";
const releaseTitle = "Scheduled unit tests are failing (release_26.2)";
c = await run({
  needs: { test: { result: "success" } },
  issueTitle: releaseTitle,
  testedSha: "release-sha",
  open: [
    { number: 10, title: devTitle },
    { number: 11, title: releaseTitle },
  ],
});
assert.deepEqual(
  c.filter(([method]) => method === "update").map(([, p]) => p.issue_number),
  [11],
);
assert.equal(
  c[1][1].body,
  "Passing again on release-sha: https://github.com/galaxyproject/galaxy/actions/runs/42",
);

// Failure details contain only the target branch's jobs and the checked-out SHA.
c = await run({
  needs: { test: { result: "failure" } },
  issueTitle: releaseTitle,
  testedSha: "release-sha",
  jobNamePrefix: "Test [release_26.2]",
  jobs: [
    { name: "Unit (dev) / Test [dev] (3.10)", conclusion: "failure" },
    {
      name: "Unit (release_26.2) / Test [release_26.2] (3.10)",
      conclusion: "failure",
    },
  ],
});
assert.equal(c.at(-1)[1].title, releaseTitle);
assert.ok(c.at(-1)[1].body.includes("Failed on release-sha:"));
assert.ok(c.at(-1)[1].body.includes("Failed jobs: Unit (release_26.2)"));
assert.ok(!c.at(-1)[1].body.includes("Unit (dev)"));

// Sibling suite failures must not leak into this suite's report for the same branch.
c = await run({
  needs: { test: { result: "failure" } },
  issueTitle: releaseTitle,
  jobNamePrefix: "Unit tests [release_26.2]",
  jobs: [
    {
      name: "Unit (release_26.2) / Unit tests [release_26.2] (3.10)",
      conclusion: "failure",
    },
    {
      name: "Tool Shed (release_26.2) / Tool Shed tests [release_26.2] (3.10, standalone)",
      conclusion: "failure",
    },
  ],
});
assert.ok(!c.at(-1)[1].body.includes("Tool Shed"));

// A version bump keeps issue identity stable and updates the existing branch issue.
c = await run({
  needs: { test: { result: "failure" } },
  issueTitle: releaseTitle,
  testedSha: "new-sha",
  open: [{ number: 11, title: releaseTitle }],
  jobs: [
    {
      name: "Unit (release_26.2) / Test [release_26.2] (3.11)",
      conclusion: "failure",
    },
  ],
});
assert.equal(c.at(-1)[0], "comment");
assert.equal(c.at(-1)[1].issue_number, 11);
console.log("all 11 reporter cases passed");

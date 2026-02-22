import { execSync, spawn } from "child_process";
import * as fs from "fs";
import * as os from "os";
import * as path from "path";
import {
  startMockServers,
  stopMockServers,
  OLLAMA_PORT,
  GITHUB_PORT,
} from "./mock-servers";

const ACT_TEST_DIR = __dirname;
const ROOT = path.resolve(ACT_TEST_DIR, "..");

// On macOS Docker Desktop, host.docker.internal resolves to the host.
// On Linux, containers reach the host via the docker bridge gateway (172.17.0.1).
const MOCK_HOST =
  process.platform === "darwin" ? "host.docker.internal" : "172.17.0.1";

// ---------------------------------------------------------------------------

function readVersion(): string {
  const pyproject = fs.readFileSync(path.join(ROOT, "pyproject.toml"), "utf-8");
  const match = pyproject.match(/^version\s*=\s*"([^"]+)"/m);
  if (!match) throw new Error("Could not read version from pyproject.toml");
  return match[1];
}

function buildAction(): void {
  console.log("\n=== Building action ===\n");
  execSync("npm run build", {
    cwd: path.join(ROOT, "action"),
    stdio: "inherit",
  });
}

function buildDockerImage(version: string): void {
  console.log("\n=== Building Docker image ===\n");
  execSync(`docker build -t kirill89/reviewcerberus:${version} .`, {
    cwd: ROOT,
    stdio: "inherit",
  });
}

function writeWorkflow(tmpDir: string): string {
  const template = fs.readFileSync(
    path.join(ACT_TEST_DIR, "fixtures", "workflow.yml.template"),
    "utf-8"
  );
  const content = template
    .replace("{{MOCK_HOST}}", MOCK_HOST)
    .replace("{{OLLAMA_PORT}}", String(OLLAMA_PORT));
  const workflowPath = path.join(tmpDir, "workflow.yml");
  fs.writeFileSync(workflowPath, content);
  return workflowPath;
}

function createTempRepo(): string {
  console.log("\n=== Creating temp repo ===\n");

  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "act-test-"));
  const git = (args: string) =>
    execSync(`git ${args}`, { cwd: tmpDir, stdio: "pipe" });

  // Init repo with main branch
  git("init");
  git("checkout -b main");

  // Copy pyproject.toml (action reads version from it)
  fs.copyFileSync(
    path.join(ROOT, "pyproject.toml"),
    path.join(tmpDir, "pyproject.toml")
  );
  fs.writeFileSync(path.join(tmpDir, "README.md"), "# Test repo\n");
  git("add .");
  git('-c user.name="test" -c user.email="test@test.com" commit -m "initial"');

  // Feature branch with known diff
  git("checkout -b test-branch");
  fs.copyFileSync(
    path.join(ACT_TEST_DIR, "fixtures", "test-file.py"),
    path.join(tmpDir, "app.py")
  );
  git("add .");
  git(
    '-c user.name="test" -c user.email="test@test.com" commit -m "add app.py"'
  );

  // Origin pointing to self (action does `git fetch origin main:main`)
  git("remote add origin .");

  // Copy action directory (not committed — act just needs it on the filesystem)
  const actionDst = path.join(tmpDir, "action");
  fs.mkdirSync(actionDst);
  fs.copyFileSync(
    path.join(ROOT, "action", "action.yml"),
    path.join(actionDst, "action.yml")
  );
  fs.cpSync(path.join(ROOT, "action", "dist"), path.join(actionDst, "dist"), {
    recursive: true,
  });

  console.log(`Temp repo created at ${tmpDir}`);
  return tmpDir;
}

function runAct(tmpDir: string, workflowPath: string): Promise<number> {
  console.log("\n=== Running act ===\n");
  return new Promise((resolve) => {
    const child = spawn(
      "act",
      [
        "pull_request",
        "--bind",
        "--env",
        `GITHUB_API_URL=http://${MOCK_HOST}:${GITHUB_PORT}`,
        "--env",
        "GITHUB_REPOSITORY=test-owner/test-repo",
        "-P",
        "ubuntu-latest=catthehacker/ubuntu:act-latest",
        "-e",
        path.join(ACT_TEST_DIR, "fixtures", "pull_request_event.json"),
        "-W",
        workflowPath,
      ],
      { cwd: tmpDir, stdio: "inherit" }
    );
    child.on("close", (code) => resolve(code ?? 1));
  });
}

// ---------------------------------------------------------------------------

async function main(): Promise<void> {
  const version = readVersion();

  buildAction();
  buildDockerImage(version);

  const tmpDir = createTempRepo();
  const workflowPath = writeWorkflow(tmpDir);

  console.log("\n=== Starting mock servers ===\n");
  await startMockServers();

  let actExit = 1;
  try {
    actExit = await runAct(tmpDir, workflowPath);
  } finally {
    await stopMockServers();
    // act's Docker containers may create root-owned files in the temp repo;
    // fs.rmSync would fail with EACCES on Linux, so shell out to rm.
    try {
      execSync(`rm -rf "${tmpDir}"`);
    } catch {
      // best-effort cleanup
    }
  }

  if (actExit !== 0) {
    process.exit(actExit);
  }
}

main();

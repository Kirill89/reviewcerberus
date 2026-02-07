import * as core from "@actions/core";
import * as fs from "fs";
import * as path from "path";

/**
 * Reads the CLI version from pyproject.toml.
 * This ensures the action uses the matching Docker image tag.
 */
export function getVersion(): string {
  const pyprojectPath = path.join(
    process.env.GITHUB_ACTION_PATH || ".",
    "..",
    "pyproject.toml"
  );

  let content: string;
  if (fs.existsSync(pyprojectPath)) {
    content = fs.readFileSync(pyprojectPath, "utf-8");
  } else {
    // Fallback: look in parent directory (when action is in action/ subdir)
    const altPath = path.join(__dirname, "..", "..", "pyproject.toml");
    if (fs.existsSync(altPath)) {
      content = fs.readFileSync(altPath, "utf-8");
    } else {
      throw new Error(
        `Could not find pyproject.toml at ${pyprojectPath} or ${altPath}`
      );
    }
  }

  const match = content.match(/^version\s*=\s*"([^"]+)"/m);
  if (!match) {
    throw new Error("Could not find version in pyproject.toml");
  }
  return match[1];
}

/**
 * Mapping from action input names to Docker environment variable names.
 * This is the single source of truth for all provider-related config.
 */
const INPUT_TO_ENV: Record<string, string> = {
  model_provider: "MODEL_PROVIDER",
  model_name: "MODEL_NAME",
  max_output_tokens: "MAX_OUTPUT_TOKENS",
  verify_model_name: "VERIFY_MODEL_NAME",
  // Bedrock
  aws_access_key_id: "AWS_ACCESS_KEY_ID",
  aws_secret_access_key: "AWS_SECRET_ACCESS_KEY",
  aws_region_name: "AWS_REGION_NAME",
  // Anthropic
  anthropic_api_key: "ANTHROPIC_API_KEY",
  // Ollama
  ollama_base_url: "OLLAMA_BASE_URL",
  // Moonshot
  moonshot_api_key: "MOONSHOT_API_KEY",
  moonshot_api_base: "MOONSHOT_API_BASE",
};

/**
 * Default values for inputs (must match action.yml)
 */
const INPUT_DEFAULTS: Record<string, string> = {
  model_provider: "bedrock",
  aws_region_name: "us-east-1",
  ollama_base_url: "http://localhost:11434",
  moonshot_api_base: "https://api.moonshot.ai/v1",
};

/**
 * Reads action inputs and returns them as Docker environment variables.
 * Only includes non-empty values.
 */
export function getDockerEnv(): Record<string, string> {
  const env: Record<string, string> = {};

  for (const [inputName, envName] of Object.entries(INPUT_TO_ENV)) {
    const value = core.getInput(inputName) || INPUT_DEFAULTS[inputName] || "";
    if (value) {
      env[envName] = value;
    }
  }

  return env;
}

/**
 * Action-specific inputs that aren't passed to Docker as env vars.
 */
export interface ActionInputs {
  githubToken: string;
  verify: boolean;
  sast: boolean;
  instructions?: string;
  minConfidence?: number;
}

/**
 * Reads action-specific inputs (not passed to Docker as env vars).
 */
export function getActionInputs(): ActionInputs {
  const githubToken = core.getInput("github_token");
  if (!githubToken) {
    throw new Error("github_token is required");
  }

  const verify = core.getInput("verify") === "true";
  const sast = core.getInput("sast") === "true";
  const instructions = core.getInput("instructions") || undefined;
  const minConfidenceStr = core.getInput("min_confidence");
  const minConfidence = minConfidenceStr
    ? parseInt(minConfidenceStr, 10)
    : undefined;

  if (minConfidence !== undefined && !verify) {
    core.warning(
      "min_confidence requires verify to be enabled. Ignoring min_confidence."
    );
  }

  return {
    githubToken,
    verify,
    sast,
    instructions,
    minConfidence: verify ? minConfidence : undefined,
  };
}

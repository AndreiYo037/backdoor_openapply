import { copyFileSync, existsSync } from "node:fs";
import { resolve } from "node:path";

const projectRoot = process.cwd();
const envPath = resolve(projectRoot, ".env");
const envExamplePath = resolve(projectRoot, ".env.example");

if (!existsSync(envPath)) {
  if (!existsSync(envExamplePath)) {
    console.error("[env] .env.example was not found. Cannot bootstrap .env.");
    process.exit(1);
  }

  copyFileSync(envExamplePath, envPath);
  console.log("[env] Created .env from .env.example.");
} else {
  console.log("[env] .env already exists.");
}

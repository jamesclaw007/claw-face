import os from "node:os";
import path from "node:path";
import { promises as fs } from "node:fs";

type AnyEvent = {
  type?: string;
  action?: string;
  name?: string;
  event?: string;
  // Most OpenClaw hook payloads are loosely typed; keep it defensive.
  context?: any;
  payload?: any;
};

const CONFIG_DIR = path.join(os.homedir(), ".config", "claw-face");
const COMMAND_FILE = path.join(CONFIG_DIR, "command.json");
const STATUS_FILE = path.join(CONFIG_DIR, "status.txt");

const VALID_EXPRESSIONS = new Set([
  // Canonical (OLED eye presets)
  "normal",
  "happy",
  "sad",
  "angry",
  "surprised",
  "suspicious",
  "cute",
  "tired",
  "wonder",
  "upset",
  "confused",
  "scared",
  "sleepy",
  "glee",
  "skeptic",
  // Compat aliases (mapped client-side)
  "neutral",
  "love",
  "focused",
  "thinking",
  "excited",
  "glitch",
  "smug",
  "sleep",
  "wink",
  "talking",
  "typing",
]);

let idleTimer: NodeJS.Timeout | undefined;

async function atomicWrite(filePath: string, contents: string): Promise<void> {
  await fs.mkdir(path.dirname(filePath), { recursive: true });
  const tmp = `${filePath}.tmp`;
  await fs.writeFile(tmp, contents, "utf8");
  await fs.rename(tmp, filePath);
}

async function writeCommand(cmd: { expression?: string; auto_cycle?: boolean }): Promise<void> {
  const out: any = {};
  if (typeof cmd.expression === "string" && VALID_EXPRESSIONS.has(cmd.expression)) {
    out.expression = cmd.expression;
  }
  if (typeof cmd.auto_cycle === "boolean") out.auto_cycle = cmd.auto_cycle;
  await atomicWrite(COMMAND_FILE, JSON.stringify(out, null, 2) + "\n");
}

async function writeStatus(text: string): Promise<void> {
  const singleLine = text.replace(/\s+/g, " ").trim();
  await fs.mkdir(CONFIG_DIR, { recursive: true });
  await fs.writeFile(STATUS_FILE, singleLine, "utf8");
}

function getEventName(e: AnyEvent): string {
  const t = (e.type || "").toString();
  const a = (e.action || "").toString();
  if (t && a) return `${t}:${a}`;
  return (e.name || e.event || t || "").toString();
}

function bestEffortCommandSummary(e: AnyEvent): string | undefined {
  const candidates = [
    e?.payload?.text,
    e?.payload?.message,
    e?.payload?.command,
    e?.context?.sessionEntry?.text,
    e?.context?.sessionEntry?.message,
    e?.context?.command?.text,
  ];
  for (const c of candidates) {
    if (typeof c === "string" && c.trim()) {
      const s = c.replace(/\s+/g, " ").trim();
      return s.length > 80 ? s.slice(0, 77) + "..." : s;
    }
  }
  return undefined;
}

function scheduleIdleFallback(): void {
  // Some OpenClaw installs don't emit a definitive "reply finished" event.
  // Keep the display from being stuck in "talking" forever.
  if (idleTimer) clearTimeout(idleTimer);
  idleTimer = setTimeout(() => {
    // Fire-and-forget: if it fails, it's not worth crashing the gateway.
    writeCommand({ expression: "normal", auto_cycle: true }).catch(() => {});
    writeStatus("Ready").catch(() => {});
  }, 30_000);
}

export default async function handler(event: AnyEvent): Promise<void> {
  const name = getEventName(event);

  if (name === "gateway:startup" || name === "agent:bootstrap") {
    if (idleTimer) clearTimeout(idleTimer);
    await writeCommand({ expression: "normal", auto_cycle: true });
    await writeStatus("Ready");
    return;
  }

  if (name === "command:new") {
    const summary = bestEffortCommandSummary(event);
    await writeCommand({ expression: "normal", auto_cycle: false });
    await writeStatus(summary ? `Working on: ${summary}` : "Working...");
    scheduleIdleFallback();
    return;
  }

  if (name === "command:reset") {
    if (idleTimer) clearTimeout(idleTimer);
    await writeCommand({ expression: "happy", auto_cycle: true });
    await writeStatus("Ready");
    return;
  }

  if (name === "command:stop") {
    if (idleTimer) clearTimeout(idleTimer);
    await writeCommand({ expression: "sleepy", auto_cycle: true });
    await writeStatus("Stopped");
    return;
  }

  if (name === "agent:error") {
    const summary = bestEffortCommandSummary(event);
    await writeCommand({ expression: "sad", auto_cycle: false });
    await writeStatus(summary ? `Error: ${summary}` : "Error");
    scheduleIdleFallback();
    return;
  }
}

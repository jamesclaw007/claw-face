import os from "node:os";
import path from "node:path";
import { promises as fs } from "node:fs";
import type { OpenClawPluginApi } from "openclaw/plugin-sdk";

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

type PresenceConfig = {
  idleExpression: string;
  busyExpression: string;
  errorExpression: string;
  autoCycleIdle: boolean;
  autoCycleBusy: boolean;
  idleDelayMs: number;
  errorHoldMs: number;
  statusMaxLen: number;
  statusPath: string;
  commandPath: string;
};

function num(v: unknown, fallback: number): number {
  const n = typeof v === "number" ? v : Number(v);
  return Number.isFinite(n) ? n : fallback;
}

function bool(v: unknown, fallback: boolean): boolean {
  if (typeof v === "boolean") return v;
  if (v === "true") return true;
  if (v === "false") return false;
  return fallback;
}

function str(v: unknown, fallback: string): string {
  return typeof v === "string" && v.trim() ? v : fallback;
}

function expandHome(p: string): string {
  if (p.startsWith("~/")) return path.join(os.homedir(), p.slice(2));
  if (p === "~") return os.homedir();
  return p;
}

function normalizeSingleLine(s: string): string {
  return s.replace(/\s+/g, " ").trim();
}

function truncate(s: string, maxLen: number): string {
  if (maxLen <= 0) return "";
  if (s.length <= maxLen) return s;
  if (maxLen <= 3) return s.slice(0, maxLen);
  return s.slice(0, maxLen - 3) + "...";
}

async function atomicWrite(filePath: string, contents: string): Promise<void> {
  const dir = path.dirname(filePath);
  await fs.mkdir(dir, { recursive: true });
  const tmp = `${filePath}.tmp.${process.pid}.${Date.now()}`;
  await fs.writeFile(tmp, contents, "utf8");
  await fs.rename(tmp, filePath);
}

function sessionKeyFromCtx(ctx: any): string {
  const sk = typeof ctx?.sessionKey === "string" && ctx.sessionKey.trim() ? ctx.sessionKey.trim() : "";
  if (sk) return sk;
  const agent = typeof ctx?.agentId === "string" && ctx.agentId.trim() ? ctx.agentId.trim() : "agent";
  return `${agent}:global`;
}

export function registerClawFacePresence(api: OpenClawPluginApi): void {
  const rawCfg = (api.pluginConfig || {}) as Record<string, unknown>;

  const cfg: PresenceConfig = {
    idleExpression: str(rawCfg.idleExpression, "normal"),
    busyExpression: str(rawCfg.busyExpression, "normal"),
    errorExpression: str(rawCfg.errorExpression, "scared"),
    autoCycleIdle: bool(rawCfg.autoCycleIdle, true),
    autoCycleBusy: bool(rawCfg.autoCycleBusy, false),
    idleDelayMs: Math.max(0, Math.floor(num(rawCfg.idleDelayMs, 1500))),
    errorHoldMs: Math.max(0, Math.floor(num(rawCfg.errorHoldMs, 60_000))),
    statusMaxLen: Math.max(0, Math.floor(num(rawCfg.statusMaxLen, 120))),
    statusPath: expandHome(str(rawCfg.statusPath, "~/.config/claw-face/status.txt")),
    commandPath: expandHome(str(rawCfg.commandPath, "~/.config/claw-face/command.json")),
  };

  if (!VALID_EXPRESSIONS.has(cfg.idleExpression)) cfg.idleExpression = "normal";
  if (!VALID_EXPRESSIONS.has(cfg.busyExpression)) cfg.busyExpression = "normal";
  if (!VALID_EXPRESSIONS.has(cfg.errorExpression)) cfg.errorExpression = "scared";

  const activeRuns = new Set<string>();
  const toolCounts = new Map<string, number>();
  let idleTimer: NodeJS.Timeout | null = null;
  let errorUntilMs = 0;

  let lastCmd = "";
  let lastStatus = "";
  let blinkSeq = 0;
  let sequenceSeq = 0;

  function busyNow(): boolean {
    if (activeRuns.size > 0) return true;
    for (const v of toolCounts.values()) if (v > 0) return true;
    return false;
  }

  function clearIdleTimer(): void {
    if (idleTimer) clearTimeout(idleTimer);
    idleTimer = null;
  }

  function clearErrorHold(): void {
    errorUntilMs = 0;
  }

  type CommandV2 = {
    expression: string;
    auto_cycle: boolean;
    intensity?: number;
    look?: { x: number; y: number };
    blink_seq?: number;
    sequence?: string;
    sequence_seq?: number;
  };

  async function writeCommand(cmd: CommandV2): Promise<void> {
    // Keep a stable key order so the lastCmd cache works as intended.
    const out: Record<string, unknown> = {
      expression: cmd.expression,
      auto_cycle: cmd.auto_cycle,
    };
    if (typeof cmd.intensity === "number" && Number.isFinite(cmd.intensity)) {
      out.intensity = Math.max(0, Math.min(1, cmd.intensity));
    }
    if (
      cmd.look &&
      typeof cmd.look.x === "number" &&
      typeof cmd.look.y === "number" &&
      Number.isFinite(cmd.look.x) &&
      Number.isFinite(cmd.look.y)
    ) {
      out.look = {
        x: Math.max(-1, Math.min(1, cmd.look.x)),
        y: Math.max(-1, Math.min(1, cmd.look.y)),
      };
    }
    if (typeof cmd.blink_seq === "number" && Number.isFinite(cmd.blink_seq)) out.blink_seq = Math.floor(cmd.blink_seq);
    if (typeof cmd.sequence === "string" && cmd.sequence.trim()) out.sequence = cmd.sequence;
    if (typeof cmd.sequence_seq === "number" && Number.isFinite(cmd.sequence_seq)) out.sequence_seq = Math.floor(cmd.sequence_seq);

    const payload = JSON.stringify(out, null, 2) + "\n";
    if (payload === lastCmd) return;
    await atomicWrite(cfg.commandPath, payload);
    lastCmd = payload;
  }

  async function writeStatus(text: string): Promise<void> {
    const norm = truncate(normalizeSingleLine(text), cfg.statusMaxLen);
    if (norm === lastStatus) return;
    await atomicWrite(cfg.statusPath, norm ? norm + "\n" : "");
    lastStatus = norm;
  }

  function noteIoError(err: unknown): void {
    api.logger.warn(`claw-face-presence: IO failed: ${String(err)}`);
  }

  function scheduleIdle(reason: string): void {
    if (cfg.idleDelayMs === 0) {
      void goIdle(reason);
      return;
    }
    clearIdleTimer();
    idleTimer = setTimeout(() => void goIdle(reason), cfg.idleDelayMs);
  }

  async function goBusy(status: string): Promise<void> {
    clearIdleTimer();
    clearErrorHold();
    try {
      await writeCommand({ expression: cfg.busyExpression, auto_cycle: cfg.autoCycleBusy, intensity: 1.0 });
      await writeStatus(status);
    } catch (err) {
      noteIoError(err);
    }
  }

  async function goIdle(reason: string): Promise<void> {
    clearIdleTimer();
    if (busyNow()) return;
    if (Date.now() < errorUntilMs) return;
    try {
      await writeCommand({ expression: cfg.idleExpression, auto_cycle: cfg.autoCycleIdle, intensity: 0.2 });
      await writeStatus("Ready");
    } catch (err) {
      noteIoError(err);
    }
    api.logger.info(`claw-face-presence: idle (${reason})`);
  }

  async function goError(msg: string): Promise<void> {
    clearIdleTimer();
    errorUntilMs = Date.now() + cfg.errorHoldMs;
    try {
      sequenceSeq += 1;
      await writeCommand({
        expression: "scared",
        auto_cycle: false,
        intensity: 1.0,
        sequence: "error_pulse",
        sequence_seq: sequenceSeq,
      });
      await writeStatus(msg);
    } catch (err) {
      noteIoError(err);
    }
  }

  api.on("gateway_start", async (event, _ctx) => {
    try {
      sequenceSeq += 1;
      await writeCommand({
        expression: cfg.idleExpression,
        auto_cycle: cfg.autoCycleIdle,
        intensity: 0.2,
        sequence: "boot",
        sequence_seq: sequenceSeq,
      });
      await writeStatus("Ready");
      api.logger.info(`claw-face-presence: gateway_start port=${String((event as any)?.port ?? "")}`);
    } catch (err) {
      noteIoError(err);
    }
  });

  api.on("gateway_stop", async () => {
    try {
      await writeCommand({ expression: "sleepy", auto_cycle: true, intensity: 0.0 });
      await writeStatus("Gateway stopped");
    } catch (err) {
      noteIoError(err);
    }
  });

  api.on("message_received", async (_event, ctx) => {
    const ch = typeof (ctx as any)?.channelId === "string" && (ctx as any).channelId ? (ctx as any).channelId : "";
    await goBusy(ch ? `Incoming (${ch})` : "Incoming");
  });

  api.on("before_agent_start", async (_event, ctx) => {
    const sk = sessionKeyFromCtx(ctx);
    activeRuns.add(sk);
    clearIdleTimer();
    clearErrorHold();
    try {
      await writeCommand({ expression: "skeptic", auto_cycle: false, intensity: 0.7 });
      await writeStatus("Thinking...");
    } catch (err) {
      noteIoError(err);
    }
  });

  api.on("agent_end", async (event, ctx) => {
    const sk = sessionKeyFromCtx(ctx);
    activeRuns.delete(sk);
    toolCounts.delete(sk);

    const ok = Boolean((event as any)?.success);
    if (!ok) {
      const err = typeof (event as any)?.error === "string" && (event as any).error.trim()
        ? normalizeSingleLine((event as any).error)
        : "Unknown error";
      await goError(`Error: ${truncate(err, cfg.statusMaxLen)}`);
      scheduleIdle("error-hold-expired");
      return;
    }

    scheduleIdle("agent_end");
  });

  api.on("before_tool_call", async (event, ctx) => {
    const sk = sessionKeyFromCtx(ctx);
    activeRuns.add(sk);
    toolCounts.set(sk, (toolCounts.get(sk) || 0) + 1);

    const tool = typeof (event as any)?.toolName === "string" && (event as any).toolName
      ? (event as any).toolName
      : (typeof (ctx as any)?.toolName === "string" ? (ctx as any).toolName : "tool");
    clearIdleTimer();
    clearErrorHold();
    try {
      await writeCommand({ expression: "suspicious", auto_cycle: false, intensity: 1.0 });
      await writeStatus(`Tool: ${tool}`);
    } catch (err) {
      noteIoError(err);
    }
  });

  api.on("after_tool_call", async (event, ctx) => {
    const sk = sessionKeyFromCtx(ctx);
    const prev = toolCounts.get(sk) || 0;
    const next = Math.max(0, prev - 1);
    if (next === 0) toolCounts.delete(sk);
    else toolCounts.set(sk, next);

    if (typeof (event as any)?.error === "string" && (event as any).error.trim()) {
      const tool = typeof (event as any)?.toolName === "string" && (event as any).toolName ? (event as any).toolName : "tool";
      const e = normalizeSingleLine((event as any).error);
      await goError(`Tool error (${tool}): ${truncate(e, cfg.statusMaxLen)}`);
      if (!busyNow()) scheduleIdle("tool_error");
      return;
    }

    if (!busyNow()) scheduleIdle("after_tool_call");
  });

  api.on("message_sending", async () => {
    clearIdleTimer();
    clearErrorHold();
    blinkSeq += 1;
    try {
      await writeCommand({
        expression: cfg.busyExpression,
        auto_cycle: cfg.autoCycleBusy,
        intensity: 1.0,
        blink_seq: blinkSeq,
      });
      await writeStatus("Sending reply...");
    } catch (err) {
      noteIoError(err);
    }
  });

  api.on("message_sent", async (event) => {
    const ok = Boolean((event as any)?.success ?? true);
    if (!ok) {
      const err = typeof (event as any)?.error === "string" && (event as any).error.trim()
        ? normalizeSingleLine((event as any).error)
        : "Send failed";
      await goError(`Error: ${truncate(err, cfg.statusMaxLen)}`);
      scheduleIdle("message_sent_error");
      return;
    }
    if (!busyNow()) scheduleIdle("message_sent");
  });

  api.logger.info(
    `claw-face-presence: loaded (commandPath=${cfg.commandPath} statusPath=${cfg.statusPath})`,
  );
}

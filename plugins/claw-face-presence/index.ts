import type { OpenClawPluginApi, OpenClawPluginConfigSchema } from "openclaw/plugin-sdk";
import { registerClawFacePresence } from "./src/presence.js";

const configSchema: OpenClawPluginConfigSchema = {
  type: "object",
  additionalProperties: false,
  properties: {
    idleExpression: { type: "string" },
    busyExpression: { type: "string" },
    errorExpression: { type: "string" },
    autoCycleIdle: { type: "boolean" },
    autoCycleBusy: { type: "boolean" },
    idleDelayMs: { type: "number" },
    errorHoldMs: { type: "number" },
    statusMaxLen: { type: "number" },
    statusPath: { type: "string" },
    commandPath: { type: "string" },
  },
};

const plugin = {
  id: "claw-face-presence",
  name: "Claw Face Presence",
  description: "Drive the claw-face kiosk (expression + status) based on real OpenClaw activity.",
  configSchema,
  register(api: OpenClawPluginApi) {
    registerClawFacePresence(api);
  },
};

export default plugin;


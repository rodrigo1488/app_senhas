"use strict";

const fs = require("fs");
const path = require("path");
const express = require("express");
const QRCode = require("qrcode");
const pino = require("pino");
const {
  default: makeWASocket,
  DisconnectReason,
  useMultiFileAuthState,
  fetchLatestBaileysVersion,
} = require("@whiskeysockets/baileys");

const PORT = Number(process.env.PORT || 3001);
const AUTH_DIR = process.env.AUTH_DIR || "/data/auth";
const INTERNAL_TOKEN = (process.env.WHATSAPP_INTERNAL_TOKEN || "").trim();
const logger = pino({ level: process.env.LOG_LEVEL || "info" });

const app = express();
app.use(express.json({ limit: "64kb" }));

let sock = null;
let lastQr = null;
let lastQrDataUrl = null;
let connectionStatus = "starting";
let connectedJid = null;
let reconnectTimer = null;
let starting = false;

function authorize(req, res, next) {
  if (!INTERNAL_TOKEN) return next();
  const header = String(req.headers["x-internal-token"] || "");
  if (header !== INTERNAL_TOKEN) {
    return res.status(401).json({ error: "Não autorizado" });
  }
  return next();
}

function toJid(destino) {
  const raw = String(destino || "").trim();
  if (!raw) return null;
  if (raw.includes("@")) return raw;
  const digits = raw.replace(/\D/g, "");
  if (!digits) return null;
  return `${digits}@s.whatsapp.net`;
}

function statusPayload() {
  return {
    status: connectionStatus,
    connected: connectionStatus === "connected",
    jid: connectedJid,
    qr: lastQr,
    qr_data_url: lastQrDataUrl,
  };
}

function clearAuth() {
  try {
    fs.mkdirSync(AUTH_DIR, { recursive: true });
    for (const name of fs.readdirSync(AUTH_DIR)) {
      fs.rmSync(path.join(AUTH_DIR, name), { recursive: true, force: true });
    }
  } catch (err) {
    logger.error(err, "Falha ao limpar auth WhatsApp");
  }
}

function endSocket() {
  if (!sock) return;
  try {
    sock.ev.removeAllListeners();
  } catch (_) {
    /* ignore */
  }
  try {
    sock.end(undefined);
  } catch (_) {
    /* ignore */
  }
  sock = null;
}

function scheduleRestart(reason, delayMs = 1000) {
  if (reconnectTimer) clearTimeout(reconnectTimer);
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null;
    restartForPairing(reason).catch((err) =>
      logger.error({ err, reason }, "Falha ao reiniciar pareamento"),
    );
  }, delayMs);
}

async function restartForPairing(reason) {
  if (starting) return;
  logger.info({ reason }, "Reiniciando WhatsApp para novo QR");
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
  endSocket();
  clearAuth();
  lastQr = null;
  lastQrDataUrl = null;
  connectedJid = null;
  connectionStatus = "starting";
  await startSocket();
}

async function startSocket() {
  if (starting) return;
  starting = true;
  try {
    fs.mkdirSync(AUTH_DIR, { recursive: true });
    const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);
    const { version } = await fetchLatestBaileysVersion();
    sock = makeWASocket({
      version,
      auth: state,
      logger: pino({ level: "silent" }),
      printQRInTerminal: false,
      syncFullHistory: false,
      markOnlineOnConnect: false,
    });

    sock.ev.on("creds.update", saveCreds);
    sock.ev.on("connection.update", async (update) => {
      const { connection, lastDisconnect, qr } = update;
      if (qr) {
        lastQr = qr;
        lastQrDataUrl = await QRCode.toDataURL(qr, { margin: 1, width: 320 });
        connectionStatus = "qr";
        connectedJid = null;
        logger.info("QR WhatsApp atualizado — escaneie no celular");
      }
      if (connection === "open") {
        connectionStatus = "connected";
        lastQr = null;
        lastQrDataUrl = null;
        connectedJid = sock?.user?.id || null;
        logger.info({ jid: connectedJid }, "WhatsApp conectado");
      }
      if (connection === "close") {
        const code = lastDisconnect?.error?.output?.statusCode;
        const loggedOut = code === DisconnectReason.loggedOut;
        const shouldReconnect = !loggedOut;
        connectedJid = null;
        sock = null;
        logger.warn({ code, shouldReconnect }, "Conexão WhatsApp fechou");
        if (shouldReconnect) {
          connectionStatus = "reconnecting";
          scheduleRestart("disconnect_retry", 3000);
          return;
        }
        // Logout remoto/local: limpa credenciais e gera QR de novo.
        connectionStatus = "logged_out";
        lastQr = null;
        lastQrDataUrl = null;
        scheduleRestart("logged_out", 800);
      }
    });
  } finally {
    starting = false;
  }
}

app.get("/health", (_req, res) => {
  res.json({ ok: true, status: connectionStatus });
});

app.get("/status", authorize, (_req, res) => {
  // Se ficou logged_out sem QR (ex.: falha ao reiniciar), tenta parear de novo.
  if (
    connectionStatus === "logged_out" &&
    !lastQrDataUrl &&
    !starting &&
    !sock &&
    !reconnectTimer
  ) {
    scheduleRestart("status_without_qr", 200);
  }
  res.json(statusPayload());
});

app.post("/send", authorize, async (req, res) => {
  try {
    if (connectionStatus !== "connected" || !sock) {
      return res.status(503).json({ error: "WhatsApp não conectado. Escaneie o QR." });
    }
    const jid = toJid(req.body?.to);
    const text = String(req.body?.text || "").trim();
    if (!jid) return res.status(400).json({ error: "Destino inválido" });
    if (!text) return res.status(400).json({ error: "Texto vazio" });
    await sock.sendMessage(jid, { text });
    return res.json({ ok: true, to: jid });
  } catch (err) {
    logger.error(err, "Falha ao enviar WhatsApp");
    return res.status(500).json({ error: err?.message || "Falha ao enviar" });
  }
});

app.post("/logout", authorize, async (_req, res) => {
  try {
    if (sock) {
      try {
        await sock.logout();
      } catch (err) {
        logger.warn({ err }, "logout do Baileys falhou; limpando sessão mesmo assim");
      }
    }
    await restartForPairing("manual_logout");
    return res.json({ ok: true, ...statusPayload() });
  } catch (err) {
    return res.status(500).json({ error: err?.message || "Falha no logout" });
  }
});

app.post("/reconnect", authorize, async (_req, res) => {
  try {
    await restartForPairing("manual_reconnect");
    return res.json({ ok: true, ...statusPayload() });
  } catch (err) {
    return res.status(500).json({ error: err?.message || "Falha ao gerar QR" });
  }
});

app.listen(PORT, "0.0.0.0", () => {
  logger.info(`WhatsApp Baileys escutando na porta ${PORT}`);
  startSocket().catch((err) => logger.error(err, "Falha ao iniciar socket"));
});

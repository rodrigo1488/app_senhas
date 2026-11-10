"use strict";

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

async function startSocket() {
  if (starting) return;
  starting = true;
  try {
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
        const shouldReconnect = code !== DisconnectReason.loggedOut;
        connectionStatus = shouldReconnect ? "reconnecting" : "logged_out";
        connectedJid = null;
        sock = null;
        logger.warn({ code, shouldReconnect }, "Conexão WhatsApp fechou");
        if (shouldReconnect) {
          if (reconnectTimer) clearTimeout(reconnectTimer);
          reconnectTimer = setTimeout(() => {
            starting = false;
            startSocket().catch((err) => logger.error(err, "Falha ao reconectar"));
          }, 3000);
          return;
        }
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
  res.json({
    status: connectionStatus,
    connected: connectionStatus === "connected",
    jid: connectedJid,
    qr: lastQr,
    qr_data_url: lastQrDataUrl,
  });
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
      await sock.logout();
    }
    connectionStatus = "logged_out";
    connectedJid = null;
    lastQr = null;
    lastQrDataUrl = null;
    sock = null;
    starting = false;
    setTimeout(() => {
      startSocket().catch((err) => logger.error(err, "Falha ao reiniciar após logout"));
    }, 1000);
    return res.json({ ok: true });
  } catch (err) {
    return res.status(500).json({ error: err?.message || "Falha no logout" });
  }
});

app.listen(PORT, "0.0.0.0", () => {
  logger.info(`WhatsApp Baileys escutando na porta ${PORT}`);
  startSocket().catch((err) => logger.error(err, "Falha ao iniciar socket"));
});

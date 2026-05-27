import makeWASocket, { useMultiFileAuthState, DisconnectReason, fetchLatestBaileysVersion } from '@whiskeysockets/baileys'
import { Boom } from '@hapi/boom'
import qrcode from 'qrcode-terminal'
import fetch from 'node-fetch'
import pino from 'pino'
import crypto from 'crypto'

const DISPATCH_URL = process.env.DISPATCH_URL || 'http://dispatch:8001'
const DISPATCH_SECRET = <REDACTED> || 'dev-secret-key'
const MY_JID = process.env.MY_WHATSAPP_JID || ''

function base64url(str) {
    return Buffer.from(str).toString('base64').replace(/=/g,'').replace(/\+/g,'-').replace(/\//g,'_')
}

function createJWT() {
    const header = base64url(JSON.stringify({alg:'HS256',typ:'JWT'}))
    const now = Math.floor(Date.now()/1000)
    const payload = base64url(JSON.stringify({sub:'whatsapp-bridge',iat:now,exp:now+86400}))
    const sig = crypto.createHmac('sha256', DISPATCH_SECRET<REDACTED>
        .update(`${header}.${payload}`)
        .digest('base64')
        .replace(/=/g,'').replace(/\+/g,'-').replace(/\//g,'_')
    return `${header}.${payload}.${sig}`
}

async function sendToDispatch(message) {
    try {
        const resp = await fetch(`${DISPATCH_URL}/dispatch`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${createJWT()}`
            },
            body: JSON.stringify({ message })
        })
        const data = await resp.json()
        return data.reply || 'Sin respuesta'
    } catch(e) {
        console.error('Error dispatch:', e.message)
        return 'Error conectando con MAX'
    }
}

async function startBot() {
    const { state, saveCreds } = await useMultiFileAuthState('./auth')
    const { version } = await fetchLatestBaileysVersion()

    const sock = makeWASocket({
        version,
        auth: state,
        logger: pino({ level: 'silent' }),
        printQRInTerminal: false
    })

    sock.ev.on('connection.update', ({ connection, lastDisconnect, qr }) => {
        if (qr) {
            console.log('\n=== Escanea este QR con WhatsApp ===\n')
            qrcode.generate(qr, { small: true })
        }
        if (connection === 'close') {
            const shouldReconnect = new Boom(lastDisconnect?.error)?.output?.statusCode !== DisconnectReason.loggedOut
            if (shouldReconnect) startBot()
        }
        if (connection === 'open') {
            console.log(`MAX conectado a WhatsApp · escuchando solo ${MY_JID}`)
        }
    })

    sock.ev.on('creds.update', saveCreds)

    sock.ev.on('messages.upsert', async ({ messages, type }) => {
        if (type !== 'notify') return

        for (const msg of messages) {
            if (!msg.message) continue

            const from = msg.key.remoteJid
            const isMe = msg.key.fromMe

            const text = msg.message.conversation ||
                         msg.message.extendedTextMessage?.text || ''

            if (!text) continue

            if (from !== MY_JID || !isMe) {
                console.log(`Ignorando: ${from} isMe:${isMe}`)
                continue
            }

            console.log(`MAX procesando: ${text.substring(0,60)}`)
            await sock.sendPresenceUpdate('composing', from)
            const reply = await sendToDispatch(text)
            await sock.sendMessage(from, { text: reply })
        }
    })
}

startBot()

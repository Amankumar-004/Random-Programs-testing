# streamlit_app.py

import streamlit as st
import streamlit.components.v1 as components
import qrcode
import io

# Set page configuration
st.set_page_config(page_title="🔒 P2P Encrypted Chat", layout="centered")
st.title("🔐 P2P Encrypted Chat")

# User input
pwd = st.text_input("Enter shared encryption password:", type="password")
room = st.text_input("Room name (any word)")

# Proceed if both fields are filled
if pwd and room:
    # Generate QR code for password sharing
    qr = qrcode.make(pwd)
    buf = io.BytesIO()
    qr.save(buf, format="PNG")
    st.image(buf, caption="Scan to share password", width=160)

    st.markdown("### Encrypted Chat")
    
    components.html(
        f"""
        <!DOCTYPE html>
        <html lang='en'>
        <head>
            <meta charset='UTF-8'>
            <title>P2P Chat</title>
            <style>
                body {{ background: #181c24; color: #f3f3f3; font-family: Arial, sans-serif; padding: 1em; }}
                input, button {{ padding: 8px; margin: 4px; border-radius: 6px; }}
                #chat {{ border: 1px solid #444; padding: 1em; height: 240px; overflow-y: auto; margin-top: 1em; background: #23283a; }}
            </style>
        </head>
        <body>
            <p><b>Room:</b> {room}</p>
            <button onclick='start(true)'>Host</button>
            <button onclick='start(false)'>Join</button><br/>
            <input id='message' type='text' placeholder='Type message' />
            <button onclick='send()'>Send</button>
            <div id='chat'></div>

            <script>
                const password = `{pwd}`;
                const room = `{room}`;
                let key, pc, channel, ws;

                async function deriveKey(pwd) {{
                    const enc = new TextEncoder();
                    const baseKey = await crypto.subtle.importKey("raw", enc.encode(pwd), "PBKDF2", false, ["deriveKey"]);
                    return crypto.subtle.deriveKey(
                        {{ name: "PBKDF2", salt: enc.encode("p2p-chat"), iterations: 50000, hash: "SHA-256" }},
                        baseKey,
                        {{ name: "AES-GCM", length: 256 }},
                        false,
                        ["encrypt", "decrypt"]
                    );
                }}

                async function encrypt(msg) {{
                    const iv = crypto.getRandomValues(new Uint8Array(12));
                    const encoded = new TextEncoder().encode(msg);
                    const ciphertext = await crypto.subtle.encrypt({{ name: "AES-GCM", iv }}, key, encoded);
                    return new Uint8Array([...iv, ...new Uint8Array(ciphertext)]);
                }}

                async function decrypt(data) {{
                    const iv = data.slice(0, 12);
                    const ciphertext = data.slice(12);
                    try {{
                        const plaintext = await crypto.subtle.decrypt({{ name: "AES-GCM", iv }}, key, ciphertext);
                        return new TextDecoder().decode(plaintext);
                    }} catch {{ return "[decryption failed]"; }}
                }}

                async function start(isHost) {{
                    key = await deriveKey(password);
                    pc = new RTCPeerConnection({{ iceServers: [{{ urls: "stun:stun.l.google.com:19302" }}] }});
                    ws = new WebSocket("wss://signal-mirror.glitch.me");

                    ws.onopen = () => {{
                        if (isHost) {{
                            channel = pc.createDataChannel("chat");
                            setup();
                            pc.createOffer().then(offer => {{
                                pc.setLocalDescription(offer);
                                ws.send(JSON.stringify({{ room, type: "offer", offer }}));
                            }});
                        }}
                    }};

                    ws.onerror = (e) => console.error("WebSocket error:", e);

                    ws.onmessage = async e => {{
                        const data = JSON.parse(e.data);
                        if (data.room !== room) return;
                        if (data.type === "offer") {{
                            await pc.setRemoteDescription(new RTCSessionDescription(data.offer));
                            const answer = await pc.createAnswer();
                            await pc.setLocalDescription(answer);
                            ws.send(JSON.stringify({{ room, type: "answer", answer }}));
                        }}
                        else if (data.type === "answer") {{
                            await pc.setRemoteDescription(new RTCSessionDescription(data.answer));
                        }}
                        else if (data.type === "candidate") {{
                            try {{ await pc.addIceCandidate(new RTCIceCandidate(data.candidate)); }} catch {{}}
                        }}
                    }};

                    pc.onicecandidate = e => {{
                        if (e.candidate) {{
                            ws.send(JSON.stringify({{ room, type: "candidate", candidate: e.candidate }}));
                        }}
                    }};

                    pc.ondatachannel = e => {{
                        channel = e.channel;
                        setup();
                    }};
                }}

                function setup() {{
                    channel.onmessage = async e => {{
                        const raw = new Uint8Array(e.data);
                        const msg = await decrypt(raw);
                        const chat = document.getElementById("chat");
                        chat.innerHTML += `<div><b>Peer:</b> ${msg}</div>`;
                        chat.scrollTop = chat.scrollHeight;
                    }};
                }}

                async function send() {{
                    const input = document.getElementById("message");
                    const text = input.value.trim();
                    if (!text) return;
                    const encrypted = await encrypt(text);
                    channel.send(encrypted);
                    const chat = document.getElementById("chat");
                    chat.innerHTML += `<div><b>You:</b> ${text}</div>`;
                    input.value = '';
                    chat.scrollTop = chat.scrollHeight;
                }}
            </script>
        </body>
        </html>
        """,
        height=500,
    )
else:
    st.info("Enter a shared password and room name above to unlock the chat.")

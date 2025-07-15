import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="🔐 P2P Encrypted Chat", layout="centered")
st.title("🔐 P2P Encrypted Chat with Theme Toggle")

pwd = st.text_input("Enter shared encryption password:", type="password")
room = st.text_input("Room name (any word)")

if pwd and room:
    st.markdown("### Share Password via QR Code")
    components.html(f"""
    <div id="qrcode" style="margin: 10px auto; width: fit-content;"></div>
    <script src="https://cdn.jsdelivr.net/npm/qrcodejs@1.0.0/qrcode.min.js"></script>
    <script>
        new QRCode(document.getElementById("qrcode"), {{
            text: `{pwd}`,
            width: 160,
            height: 160,
            colorDark : "#000000",
            colorLight : "#ffffff",
            correctLevel : QRCode.CorrectLevel.H
        }});
    </script>
    """, height=180)

    st.markdown("### Encrypted Chat")

    components.html(
        f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style id="theme-style"></style>
        </head>
        <body>
            <button onclick="toggleTheme()" style="float:right;margin-bottom:10px;">🌗 Toggle Theme</button>
            <div style="clear:both;"></div>
            <p><b>Room:</b> {room}</p>
            <button onclick='start(true)'>Host</button>
            <button onclick='start(false)'>Join</button><br/>
            <input id='message' type='text' placeholder='Type message' />
            <button onclick='send()'>Send</button>
            <div id='chat' class='chatbox'></div>

            <script>
                const password = `{pwd}`;
                const room = `{room}`;
                let key, pc, channel, ws;

                const darkTheme = `
                    body {{ background: #111; color: #fff; font-family: sans-serif; padding: 1em; }}
                    .chatbox {{ background: #1c1c1c; border-radius: 12px; padding: 1em; height: 300px; overflow-y: auto; }}
                    input {{ width: 70%; padding: 10px; border-radius: 8px; border: none; }}
                    button {{ padding: 10px 16px; border: none; border-radius: 8px; background: #4e88ff; color: white; font-weight: bold; }}
                    .bubble {{ margin: 6px 0; display: flex; align-items: flex-start; }}
                    .bubble img {{ width: 28px; height: 28px; border-radius: 50%; margin-right: 8px; }}
                    .bubble .msg {{ background: #2a2a2a; padding: 8px 12px; border-radius: 8px; max-width: 70%; word-wrap: break-word; }}
                    .you .msg {{ background: #4e88ff; color: white; }}
                `;

                const lightTheme = `
                    body {{ background: #f5f5f5; color: #222; font-family: sans-serif; padding: 1em; }}
                    .chatbox {{ background: #fff; border-radius: 12px; padding: 1em; height: 300px; overflow-y: auto; border: 1px solid #ccc; }}
                    input {{ width: 70%; padding: 10px; border-radius: 8px; border: 1px solid #ccc; }}
                    button {{ padding: 10px 16px; border: none; border-radius: 8px; background: #1976d2; color: white; font-weight: bold; }}
                    .bubble {{ margin: 6px 0; display: flex; align-items: flex-start; }}
                    .bubble img {{ width: 28px; height: 28px; border-radius: 50%; margin-right: 8px; }}
                    .bubble .msg {{ background: #eee; padding: 8px 12px; border-radius: 8px; max-width: 70%; word-wrap: break-word; }}
                    .you .msg {{ background: #1976d2; color: white; }}
                `;

                let currentTheme = "dark";
                document.getElementById("theme-style").innerHTML = darkTheme;

                function toggleTheme() {{
                    currentTheme = currentTheme === "dark" ? "light" : "dark";
                    document.getElementById("theme-style").innerHTML = currentTheme === "dark" ? darkTheme : lightTheme;
                }}

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

                    ws.onmessage = async e => {{
                        const data = JSON.parse(e.data);
                        if (data.room !== room) return;
                        if (data.type === "offer") {{
                            await pc.setRemoteDescription(new RTCSessionDescription(data.offer));
                            const answer = await pc.createAnswer();
                            await pc.setLocalDescription(answer);
                            ws.send(JSON.stringify({{ room, type: "answer", answer }}));
                        }} else if (data.type === "answer") {{
                            await pc.setRemoteDescription(new RTCSessionDescription(data.answer));
                        }} else if (data.type === "candidate") {{
                            try {{ await pc.addIceCandidate(new RTCIceCandidate(data.candidate)); }} catch {{}}
                        }}
                    }};

                    pc.onicecandidate = e => e.candidate && ws.send(JSON.stringify({{ room, type: "candidate", candidate: e.candidate }}));
                    pc.ondatachannel = e => (channel = e.channel, setup());

                    if (isHost) {{
                        channel = pc.createDataChannel("chat");
                        setup();
                        const offer = await pc.createOffer();
                        await pc.setLocalDescription(offer);
                        ws.onopen = () => ws.send(JSON.stringify({{ room, type: "offer", offer }}));
                    }}
                }}

                function setup() {{
                    channel.onmessage = async e => {{
                        const raw = new Uint8Array(e.data);
                        const msg = await decrypt(raw);
                        const chat = document.getElementById("chat");
                        chat.innerHTML += `
                            <div class="bubble peer">
                                <img src="https://avatars.githubusercontent.com/u/9919?s=40" />
                                <div class="msg"><b>Peer:</b> ${{msg}}</div>
                            </div>`;
                        chat.scrollTop = chat.scrollHeight;
                    }};
                }}

                async function send() {{
                    const input = document.getElementById("message");
                    if (!input.value) return;
                    const chat = document.getElementById("chat");
                    const encrypted = await encrypt(input.value);
                    channel.send(encrypted);
                    chat.innerHTML += `
                        <div class="bubble you">
                            <img src="https://avatars.githubusercontent.com/u/2?v=4" />
                            <div class="msg"><b>You:</b> ${{input.value}}</div>
                        </div>`;
                    input.value = '';
                    chat.scrollTop = chat.scrollHeight;
                }}
            </script>
        </body>
        </html>
        """,
        height=650,
    )
else:
    st.info("Enter a shared password and room name above to unlock the chat.")

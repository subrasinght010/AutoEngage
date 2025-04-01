const signalingServerUrl = "wss://pvc66t9j-8080.inc1.devtunnels.ms/ws";
const audioStreamUrl = "wss://pvc66t9j-8080.inc1.devtunnels.ms/audio_stream";
const peerId = Math.random().toString(36).substr(2, 9);
let localConnection, remotePeerId, localStream, signalingSocket, audioSocket, mediaRecorder;

function connectWebSocket(url, onMessage) {
    const token = document.cookie.split('; ').find(row => row.startsWith('access_token='))?.split('=')[1];

    if (!token) {
        console.error("❌ No JWT token found! WebSocket authentication will fail.");
        return;
    }

    let socket = new WebSocket(url);

    socket.onopen = () => {
        console.log("✅ WebSocket connected:", url);
        
        // ✅ Send token as first message for authentication
        socket.send(JSON.stringify({ type: "auth", token: token }));
    };

    socket.onerror = (error) => {
        console.error("❌ WebSocket error:", error);
    };

    socket.onclose = (event) => {
        console.warn(`⚠️ WebSocket closed: ${url}`, event.reason);

        if (!event.wasClean) {
            console.log("🔄 Reconnecting WebSocket...");
            setTimeout(() => {
                connectWebSocket(url, onMessage);
            }, 3000);
        }
    };

    socket.onmessage = onMessage;
    return socket;
}


async function startWebRTC() {
    console.log("🎬 Starting WebRTC...");

    signalingSocket = connectWebSocket(signalingServerUrl, async (event) => {
        const message = JSON.parse(event.data);
        console.log("📩 Signaling Message Received:", message);

        if (message.type === "offer") await handleOffer(message);
        if (message.type === "answer") await handleAnswer(message);
        if (message.type === "ice-candidate") await handleIceCandidate(message);
    });

    audioSocket = connectWebSocket(audioStreamUrl, async (event) => {
        console.log("🔊 Audio Data Received");
        const arrayBuffer = await event.data.arrayBuffer();
        playAudio(arrayBuffer);
    });

    localStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    document.getElementById("callButton").addEventListener("click", startCall);

    localConnection = new RTCPeerConnection({
        iceServers: [
            { urls: "stun:stun.l.google.com:19302" },
            { urls: "turn:your-turn-server.com:3478", username: "yourUsername", credential: "yourPassword" }
        ],
    });

    localStream.getTracks().forEach(track => localConnection.addTrack(track, localStream));

    localConnection.onicecandidate = (event) => {
        if (event.candidate) {
            signalingSocket.send(JSON.stringify({
                type: "ice-candidate",
                peer_id: peerId,
                target_peer: remotePeerId,
                candidate: event.candidate,
            }));
        }
    };

    localConnection.ontrack = (event) => {
        console.log("🎧 Remote audio stream received");
        document.getElementById("remoteAudio").srcObject = event.streams[0];
    };

    streamAudio();
}

async function startCall() {
    if (!signalingSocket || signalingSocket.readyState !== WebSocket.OPEN) {
        console.error("❌ Cannot start call: Signaling WebSocket is not open.");
        alert("Signaling server is not connected.");
        return;
    }

    remotePeerId = document.getElementById("targetPeerId").value;
    if (!remotePeerId) {
        alert("Enter target Peer ID");
        return;
    }

    const offer = await localConnection.createOffer();
    await localConnection.setLocalDescription(offer);

    signalingSocket.send(JSON.stringify({
        type: "offer",
        peer_id: peerId,
        target_peer: remotePeerId,
        offer: offer,
    }));

    console.log("📤 Sent Offer to:", remotePeerId);
}

async function streamAudio() {
    const mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });

    mediaRecorder = new MediaRecorder(mediaStream);
    mediaRecorder.start(1000);

    mediaRecorder.ondataavailable = async (event) => {
        if (audioSocket && audioSocket.readyState === WebSocket.OPEN) {
            console.log("📤 Sending Audio Data");
            audioSocket.send(event.data);
        }
    };
}

window.onload = startWebRTC;

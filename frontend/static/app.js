const voiceChatUrl = "wss://pvc66t9j-8080.inc1.devtunnels.ms/voice_chat";  // Merged WebSocket URL
const peerId = Math.random().toString(36).substr(2, 9);  // Generate unique peerId for this client
let localConnection, remotePeerId, localStream, voiceChatSocket, mediaRecorder;
let isMuted = false;
let isCallActive = false; // ✅ Prevents auto-calling on page load
let reconnectTimeout;

const statusElement = document.getElementById("connectionStatus");
const conversationBox = document.getElementById("conversation");
const muteButton = document.getElementById("muteButton");
const callButton = document.getElementById("callButton");
const disconnectButton = document.getElementById("disconnectButton"); // ✅ New Button for Ending Calls

// Ensure WebSocket is open before sending data
function sendWebSocketData(socket, data) {
    if (socket.readyState === WebSocket.OPEN) {
        socket.send(data);
        console.log("📤 Data sent to WebSocket.");
    } else if (socket.readyState === WebSocket.CONNECTING) {
        console.log("⚠️ WebSocket is still connecting. Data not sent yet.");
    } else {
        console.error("❌ WebSocket is not open. Data cannot be sent.");
    }
}

// WebSocket Connection Function (Merged for both signaling and audio)
function connectWebSocket(url, onMessage, onOpen) {
    const token = document.cookie.split('; ').find(row => row.startsWith('access_token='))?.split('=')[1];

    if (!token) {
        console.error("❌ No JWT token found! WebSocket authentication will fail.");
        return;
    }

    let socket = new WebSocket(url);

    socket.binaryType = "arraybuffer"; // Ensure binary data is handled properly

    socket.onopen = () => {
        console.log("✅ WebSocket connected:", url);
        statusElement.textContent = "Connected";
        statusElement.style.color = "green";
        
        // Send authentication message with peerId and token when WebSocket connection is open
        socket.send(JSON.stringify({
            type: "auth",
            token: token,
            peer_id: peerId  // Send the unique peerId to the server for identification
        }));

        // Trigger the onOpen callback after the WebSocket is open
        if (onOpen) onOpen(socket);
    };

    socket.onerror = (error) => {
        console.error("❌ WebSocket error:", error);
    };

    socket.onclose = (event) => {
        console.warn(`⚠️ WebSocket closed: ${url}`, event.reason);
        statusElement.textContent = "Disconnected";
        statusElement.style.color = "red";

        // Attempt to reconnect after 3 seconds
        setTimeout(() => {
            console.log("🔄 Attempting to reconnect WebSocket...");
            connectWebSocket(url, onMessage, onOpen);
        }, 3000);
    };

    socket.onmessage = onMessage;
    return socket;
}

// WebRTC Setup Function
async function setupWebRTC() {
    console.log("🎬 Starting WebRTC...");
    
    voiceChatSocket = connectWebSocket(voiceChatUrl, async (event) => {
        const message = JSON.parse(event.data);
        console.log("📩 Message Received:", message);
        if (message.type === "offer") await handleOffer(message);
        if (message.type === "answer") await handleAnswer(message);
        if (message.type === "ice-candidate") await handleIceCandidate(message);
        if (message.type === "audio") await playAudio(event.data);  // Handle incoming audio data
    }, (socket) => {
        // WebSocket is open, now we can start the call
        callButton.disabled = false;  // Enable the call button once WebSocket is connected
    });

    localStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    muteButton.addEventListener("click", toggleMute);
    disconnectButton.addEventListener("click", endCall);
    
    localConnection = new RTCPeerConnection({
        iceServers: [
            { urls: "stun:stun.l.google.com:19302" },
            { urls: "turn:your-turn-server.com:3478", username: "yourUsername", credential: "yourPassword" }
        ],
    });
    
    localStream.getTracks().forEach(track => localConnection.addTrack(track, localStream));

    localConnection.onicecandidate = (event) => {
        if (event.candidate) {
            voiceChatSocket.send(JSON.stringify({
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

    streamAudio();  // Capture and stream audio to WebSocket
}

// Stream Audio Function
async function streamAudio() {
    const mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });

    mediaRecorder = new MediaRecorder(mediaStream);
    mediaRecorder.start(1000);  // Capture audio in chunks

    mediaRecorder.ondataavailable = async (event) => {
        if (voiceChatSocket && voiceChatSocket.readyState === WebSocket.OPEN && !isMuted) {
            console.log("📤 Sending Audio Data");
            sendWebSocketData(voiceChatSocket, event.data);  // Send the audio blob data safely
        }
    };
}

// Start Call Function
async function startCall() {
    if (!voiceChatSocket || voiceChatSocket.readyState !== WebSocket.OPEN) {
        console.error("❌ Cannot start call: WebSocket is not open.");
        alert("WebSocket server is not connected.");
        return;
    }

    remotePeerId = document.getElementById("targetPeerId").value;
    if (!remotePeerId) {
        alert("Enter target Peer ID");
        return;
    }

    isCallActive = true; // ✅ Prevent reconnect loop during active call
    const offer = await localConnection.createOffer();
    await localConnection.setLocalDescription(offer);
    
    voiceChatSocket.send(JSON.stringify({
        type: "offer",
        peer_id: peerId,
        target_peer: remotePeerId,
        offer: offer,
    }));

    console.log("📤 Sent Offer to:", remotePeerId);
}

// Mute/Unmute Function
function toggleMute() {
    isMuted = !isMuted;
    muteButton.textContent = isMuted ? "Unmute" : "Mute";
    console.log(isMuted ? "🔇 Muted" : "🔊 Unmuted");
}

// End Call Function
function endCall() {
    console.log("📞 Ending Call...");
    
    if (localConnection) {
        localConnection.close();
        localConnection = null;
    }

    if (voiceChatSocket) {
        closeWebSocket(voiceChatSocket);  // Close WebSocket
        voiceChatSocket = null;
    }

    isCallActive = false;
    statusElement.textContent = "Call Disconnected";
    statusElement.style.color = "red";

    alert("Call Ended");
}

// Close WebSocket gracefully without attempting to send data
function closeWebSocket(socket) {
    if (socket && socket.readyState === WebSocket.OPEN) {
        console.log("Closing WebSocket...");
        socket.close();
    } else {
        console.log("WebSocket already closed or in closing state.");
    }
}

// Play Audio Function
function playAudio(arrayBuffer) {
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    audioContext.decodeAudioData(arrayBuffer, (buffer) => {
        const source = audioContext.createBufferSource();
        source.buffer = buffer;
        source.connect(audioContext.destination);
        source.start(0);
    });
}

// Wait for DOM Content Loaded
document.addEventListener('DOMContentLoaded', function () {
    // Initially disable the call button
    callButton.disabled = true; 

    // Start the WebRTC process when the call button is clicked
    callButton.addEventListener("click", async () => {
        await setupWebRTC(); // Setup WebRTC only when call button is clicked
        startCall(); // Proceed with starting the call
    });
});

// "wss://pvc66t9j-8080.inc1.devtu:8080/voice_chat"
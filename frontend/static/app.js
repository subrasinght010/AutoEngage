// // const signalingServerUrl = "wss://pvc66t9j-8080.inc1.devtunnels.ms/ws";
// // const audioStreamUrl = "wss://pvc66t9j-8080.inc1.devtunnels.ms/audio_stream";
// // const peerId = Math.random().toString(36).substr(2, 9);
// // let localConnection, remotePeerId, localStream, signalingSocket, audioSocket, mediaRecorder;
// // let isMuted = false;

// // const statusElement = document.getElementById("connectionStatus");
// // const conversationBox = document.getElementById("conversation");
// // const muteButton = document.getElementById("muteButton");
// // const callButton = document.getElementById("callButton");

// // function connectWebSocket(url, onMessage) {
// //     const token = document.cookie.split('; ').find(row => row.startsWith('access_token='))?.split('=')[1];

// //     if (!token) {
// //         console.error("❌ No JWT token found! WebSocket authentication will fail.");
// //         return;
// //     }

// //     let socket = new WebSocket(url);

// //     socket.onopen = () => {
// //         console.log("✅ WebSocket connected:", url);
// //         statusElement.textContent = "Connected";
// //         statusElement.style.color = "green";
// //         socket.send(JSON.stringify({ type: "auth", token: token }));
// //     };

// //     socket.onerror = (error) => {
// //         console.error("❌ WebSocket error:", error);
// //     };

// //     socket.onclose = (event) => {
// //         console.warn(`⚠️ WebSocket closed: ${url}`, event.reason);
// //         statusElement.textContent = "Disconnected";
// //         statusElement.style.color = "red";
        
// //         setTimeout(() => {
// //             connectWebSocket(url, onMessage);
// //         }, 3000);
// //     };

// //     socket.onmessage = onMessage;
// //     return socket;
// // }

// // async function startWebRTC() {
// //     console.log("🎬 Starting WebRTC...");
    
// //     signalingSocket = connectWebSocket(signalingServerUrl, async (event) => {
// //         const message = JSON.parse(event.data);
// //         console.log("📩 Signaling Message Received:", message);
// //         if (message.type === "offer") await handleOffer(message);
// //         if (message.type === "answer") await handleAnswer(message);
// //         if (message.type === "ice-candidate") await handleIceCandidate(message);
// //     });

// //     audioSocket = connectWebSocket(audioStreamUrl, async (event) => {
// //         console.log("🔊 Audio Data Received");
// //         const arrayBuffer = await event.data.arrayBuffer();
// //         playAudio(arrayBuffer);
// //     });

// //     localStream = await navigator.mediaDevices.getUserMedia({ audio: true });
// //     callButton.addEventListener("click", startCall);
// //     muteButton.addEventListener("click", toggleMute);
    
// //     localConnection = new RTCPeerConnection({
// //         iceServers: [
// //             { urls: "stun:stun.l.google.com:19302" },
// //             { urls: "turn:your-turn-server.com:3478", username: "yourUsername", credential: "yourPassword" }
// //         ],
// //     });
    
// //     localStream.getTracks().forEach(track => localConnection.addTrack(track, localStream));

// //     localConnection.onicecandidate = (event) => {
// //         if (event.candidate) {
// //             signalingSocket.send(JSON.stringify({
// //                 type: "ice-candidate",
// //                 peer_id: peerId,
// //                 target_peer: remotePeerId,
// //                 candidate: event.candidate,
// //             }));
// //         }
// //     };

// //     localConnection.ontrack = (event) => {
// //         console.log("🎧 Remote audio stream received");
// //         document.getElementById("remoteAudio").srcObject = event.streams[0];
// //     };

// //     streamAudio();
// // }

// // async function startCall() {
// //     if (!signalingSocket || signalingSocket.readyState !== WebSocket.OPEN) {
// //         console.error("❌ Cannot start call: Signaling WebSocket is not open.");
// //         alert("Signaling server is not connected.");
// //         return;
// //     }

// //     remotePeerId = document.getElementById("targetPeerId").value;
// //     if (!remotePeerId) {
// //         alert("Enter target Peer ID");
// //         return;
// //     }

// //     const offer = await localConnection.createOffer();
// //     await localConnection.setLocalDescription(offer);
    
// //     signalingSocket.send(JSON.stringify({
// //         type: "offer",
// //         peer_id: peerId,
// //         target_peer: remotePeerId,
// //         offer: offer,
// //     }));

// //     console.log("📤 Sent Offer to:", remotePeerId);
// // }

// // async function streamAudio() {
// //     const mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
// //     mediaRecorder = new MediaRecorder(mediaStream);
// //     mediaRecorder.start(1000);

// //     mediaRecorder.ondataavailable = async (event) => {
// //         if (audioSocket && audioSocket.readyState === WebSocket.OPEN && !isMuted) {
// //             console.log("📤 Sending Audio Data");
// //             audioSocket.send(event.data);
// //         }
// //     };
// // }

// // function toggleMute() {
// //     isMuted = !isMuted;
// //     muteButton.textContent = isMuted ? "Unmute" : "Mute";
// //     console.log(isMuted ? "🔇 Muted" : "🔊 Unmuted");
// // }

// // function playAudio(arrayBuffer) {
// //     const audioContext = new (window.AudioContext || window.webkitAudioContext)();
// //     audioContext.decodeAudioData(arrayBuffer, (buffer) => {
// //         const source = audioContext.createBufferSource();
// //         source.buffer = buffer;
// //         source.connect(audioContext.destination);
// //         source.start(0);
// //     });
// // }

// // window.onload = startWebRTC;



// const signalingServerUrl = "wss://pvc66t9j-8080.inc1.devtunnels.ms/ws";
// const audioStreamUrl = "wss://pvc66t9j-8080.inc1.devtunnels.ms/audio_stream";
// const peerId = Math.random().toString(36).substr(2, 9);
// let localConnection, remotePeerId, localStream, signalingSocket, audioSocket, mediaRecorder;
// let isMuted = false;

// const statusElement = document.getElementById("connectionStatus");
// const conversationBox = document.getElementById("conversation");
// const muteButton = document.getElementById("muteButton");
// const callButton = document.getElementById("callButton");
// const disconnectButton = document.getElementById("disconnectButton");

// async function initializeWebRTC() {
//     console.log("🎬 Initializing WebRTC...");

//     signalingSocket = connectWebSocket(signalingServerUrl, async (event) => {
//         const message = JSON.parse(event.data);
//         console.log("📩 Signaling Message Received:", message);
//         if (message.type === "offer") await handleOffer(message);
//         if (message.type === "answer") await handleAnswer(message);
//         if (message.type === "ice-candidate") await handleIceCandidate(message);
//     });

//     // audioSocket = connectWebSocket(audioStreamUrl, async (event) => {
//     //     console.log("🔊 Audio Data Received");
//     //     const arrayBuffer = await event.data.arrayBuffer();
//     //     playAudio(arrayBuffer);
//     // });

//     audioSocket = connectWebSocket(audioStreamUrl, async (event) => {
//         console.log("🔊 Audio Data Received");
    
//         // Ensure it's received as an ArrayBuffer
//         if (event.data instanceof Blob) {
//             const arrayBuffer = await event.data.arrayBuffer();
//             playAudio(arrayBuffer);
//         } else if (event.data instanceof ArrayBuffer) {
//             playAudio(event.data);
//         } else {
//             console.error("❌ Invalid audio data format received:", event.data);
//         }
//     });

//     localStream = await navigator.mediaDevices.getUserMedia({ audio: true });

//     localConnection = new RTCPeerConnection({
//         iceServers: [
//             { urls: "stun:stun.l.google.com:19302" },
//             { urls: "turn:your-turn-server.com:3478", username: "yourUsername", credential: "yourPassword" }
//         ],
//     });

//     localStream.getTracks().forEach(track => localConnection.addTrack(track, localStream));

//     localConnection.onicecandidate = (event) => {
//         if (event.candidate) {
//             signalingSocket.send(JSON.stringify({
//                 type: "ice-candidate",
//                 peer_id: peerId,
//                 target_peer: remotePeerId,
//                 candidate: event.candidate,
//             }));
//         }
//     };

//     localConnection.ontrack = (event) => {
//         console.log("🎧 Remote audio stream received");
//         document.getElementById("remoteAudio").srcObject = event.streams[0];
//     };

//     console.log("✅ WebRTC Initialized Successfully.");
// }

// async function startCall() {
//     if (!signalingSocket || signalingSocket.readyState !== WebSocket.OPEN) {
//         console.error("❌ Cannot start call: Signaling WebSocket is not open.");
//         alert("Signaling server is not connected.");
//         return;
//     }

//     remotePeerId = document.getElementById("targetPeerId").value;
//     if (!remotePeerId) {
//         alert("Enter target Peer ID");
//         return;
//     }

//     console.log("📞 Starting Call with", remotePeerId);
    
//     const offer = await localConnection.createOffer();
//     await localConnection.setLocalDescription(offer);
    
//     signalingSocket.send(JSON.stringify({
//         type: "offer",
//         peer_id: peerId,
//         target_peer: remotePeerId,
//         offer: offer,
//     }));

//     console.log("📤 Sent Offer to:", remotePeerId);
// }

// async function disconnectCall() {
//     console.log("📴 Disconnecting Call...");

//     if (localConnection) {
//         localConnection.close();
//         localConnection = null;
//     }

//     if (signalingSocket) {
//         signalingSocket.close();
//         signalingSocket = null;
//     }

//     if (audioSocket) {
//         audioSocket.close();
//         audioSocket = null;
//     }

//     if (mediaRecorder) {
//         mediaRecorder.stop();
//     }

//     if (localStream) {
//         localStream.getTracks().forEach(track => track.stop());
//         localStream = null;
//     }

//     statusElement.textContent = "Disconnected";
//     statusElement.style.color = "red";
//     console.log("✅ Call Disconnected.");
// }

// // Function to continuously stream audio
// async function streamAudio() {
//     const mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
//     mediaRecorder = new MediaRecorder(mediaStream);
//     mediaRecorder.start(1000);

//     mediaRecorder.ondataavailable = async (event) => {
//         if (audioSocket && audioSocket.readyState === WebSocket.OPEN && !isMuted) {
//             console.log("📤 Sending Audio Data");
//             audioSocket.send(event.data);
//         }
//     };
// }

// // Function to toggle mute/unmute
// function toggleMute() {
//     isMuted = !isMuted;
//     muteButton.textContent = isMuted ? "Unmute" : "Mute";
//     console.log(isMuted ? "🔇 Muted" : "🔊 Unmuted");
// }

// // Function to play received audio
// function playAudio(arrayBuffer) {
//     const audioContext = new (window.AudioContext || window.webkitAudioContext)();
//     audioContext.decodeAudioData(arrayBuffer, (buffer) => {
//         const source = audioContext.createBufferSource();
//         source.buffer = buffer;
//         source.connect(audioContext.destination);
//         source.start(0);
//     });
// }

// // Function to connect WebSockets
// function connectWebSocket(url, onMessage) {
//     const token = document.cookie.split('; ').find(row => row.startsWith('access_token='))?.split('=')[1];

//     if (!token) {
//         console.error("❌ No JWT token found! WebSocket authentication will fail.");
//         return;
//     }

//     let socket = new WebSocket(url);

//     socket.onopen = () => {
//         console.log("✅ WebSocket connected:", url);
//         statusElement.textContent = "Connected";
//         statusElement.style.color = "green";
//         socket.send(JSON.stringify({ type: "auth", token: token }));
//     };

//     socket.onerror = (error) => {
//         console.error("❌ WebSocket error:", error);
//     };

//     socket.onclose = (event) => {
//         console.warn(`⚠️ WebSocket closed: ${url}`, event.reason);
//         statusElement.textContent = "Disconnected";
//         statusElement.style.color = "red";
        
//         setTimeout(() => {
//             connectWebSocket(url, onMessage);
//         }, 3000);
//     };

//     socket.onmessage = onMessage;
//     return socket;
// }

// // Initialize WebRTC on page load
// window.onload = async () => {
//     await initializeWebRTC();
//     callButton.addEventListener("click", startCall);
//     muteButton.addEventListener("click", toggleMute);
//     disconnectButton.addEventListener("click", disconnectCall);
// };


const signalingServerUrl = "wss://pvc66t9j-8080.inc1.devtunnels.ms/ws";
const audioStreamUrl = "wss://pvc66t9j-8080.inc1.devtunnels.ms/audio_stream";
const peerId = Math.random().toString(36).substr(2, 9);
let localConnection, remotePeerId, localStream, signalingSocket, audioSocket, mediaRecorder;
let isMuted = false;

const statusElement = document.getElementById("connectionStatus");
const callButton = document.getElementById("callButton");
const disconnectButton = document.getElementById("disconnectButton");
const muteButton = document.getElementById("muteButton");

function connectWebSocket(url, onMessage) {
    const token = document.cookie.split('; ').find(row => row.startsWith('access_token='))?.split('=')[1];

    if (!token) {
        console.error("❌ No JWT token found! WebSocket authentication will fail.");
        return;
    }

    let socket = new WebSocket(url);

    socket.onopen = () => {
        console.log("✅ WebSocket connected:", url);
        statusElement.textContent = "Connected";
        statusElement.style.color = "green";
        socket.send(JSON.stringify({ type: "auth", token: token }));
    };

    socket.onerror = (error) => {
        console.error("❌ WebSocket error:", error);
    };

    socket.onclose = (event) => {
        console.warn(`⚠️ WebSocket closed: ${url}`, event.reason);
        statusElement.textContent = "Disconnected";
        statusElement.style.color = "red";
        
        setTimeout(() => {
            connectWebSocket(url, onMessage);
        }, 3000);
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

        // Ensure it's received as an ArrayBuffer
        if (event.data instanceof Blob) {
            const arrayBuffer = await event.data.arrayBuffer();
            playAudio(arrayBuffer);
        } else if (event.data instanceof ArrayBuffer) {
            playAudio(event.data);
        } else {
            console.error("❌ Invalid audio data format received:", event.data);
        }
    });

    localStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    callButton.addEventListener("click", startCall);
    disconnectButton.addEventListener("click", disconnectCall);
    muteButton.addEventListener("click", toggleMute);

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
    console.log("✅ WebRTC Initialized Successfully.");

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

    callButton.disabled = true;
    disconnectButton.disabled = false;
    console.log("📤 Sent Offer to:", remotePeerId);
}

async function streamAudio() {
    const mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(mediaStream);
    mediaRecorder.start(1000);

    mediaRecorder.ondataavailable = async (event) => {
        if (audioSocket && audioSocket.readyState === WebSocket.OPEN && !isMuted) {
            console.log("📤 Sending Audio Data");

            const audioBlob = event.data;
            const arrayBuffer = await audioBlob.arrayBuffer(); // Ensure proper binary format

            audioSocket.send(arrayBuffer);
        }
    };
}

function disconnectCall() {
    console.log("🔴 Disconnecting call...");
    localConnection.close();
    audioSocket.close();
    signalingSocket.close();

    callButton.disabled = false;
    disconnectButton.disabled = true;
    statusElement.textContent = "Disconnected";
    statusElement.style.color = "red";
}

function toggleMute() {
    isMuted = !isMuted;
    muteButton.textContent = isMuted ? "Unmute" : "Mute";
    console.log(isMuted ? "🔇 Muted" : "🔊 Unmuted");
}

function playAudio(arrayBuffer) {
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    audioContext.decodeAudioData(arrayBuffer, (buffer) => {
        const source = audioContext.createBufferSource();
        source.buffer = buffer;
        source.connect(audioContext.destination);
        source.start(0);
    });
}

window.onload = startWebRTC;


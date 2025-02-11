const video = document.getElementById("video");

// Acceder a la cámara y empezar a grabar automáticamente
navigator.mediaDevices.getUserMedia({ video: true })
    .then(stream => {
        video.srcObject = stream;

        // Crear un canal de comunicación para enviar el video al backend
        const socket = new WebSocket('ws://127.0.0.1:8000/video-stream');

        // Configuración de la grabación y envío de frames
        const mediaRecorder = new MediaRecorder(stream);
        mediaRecorder.ondataavailable = async (event) => {
            const blob = event.data;

            // Enviar el blob (video) al backend a través del WebSocket
            socket.send(blob);
        };

        // Iniciar la grabación automáticamente
        mediaRecorder.start(1000);  // 1000ms = 1 segundo de grabación

    })
    .catch(err => console.error("Error accediendo a la cámara", err));

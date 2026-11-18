const recordToggle = document.getElementById('recordToggle');
const recordLabel = document.getElementById('recordLabel');
const recordDot = recordToggle.querySelector('.record-dot');
const audioInput = document.getElementById('audioInput');
const saveButton = document.getElementById('saveButton');
const timer = document.getElementById('timer');
const statusText = document.getElementById('statusText');
const captureStatus = document.getElementById('captureStatus');
const saveHint = document.getElementById('saveHint');

let mediaRecorder;
let chunks = [];
let stream;
let startedAt;
let timerInterval;

// Convert an elapsed duration in seconds into a two-digit minute/second string.
function formatTime(seconds) {
  const minutes = Math.floor(seconds / 60).toString().padStart(2, '0');
  const remainder = Math.floor(seconds % 60).toString().padStart(2, '0');
  return `${minutes}:${remainder}`;
}

// Request microphone access, configure MediaRecorder, and begin a new recording.
async function startRecording() {
  if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
    statusText.textContent = 'Audio recording is not supported here';
    saveHint.textContent = 'Open the app in Chrome, Edge, or Firefox.';
    return;
  }

  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const preferred = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4', 'audio/ogg'];
    const mimeType = preferred.find(type => MediaRecorder.isTypeSupported(type)) || '';
    mediaRecorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
    chunks = [];

    mediaRecorder.addEventListener('dataavailable', event => {
      if (event.data.size) chunks.push(event.data);
    });

    mediaRecorder.addEventListener('stop', () => {
      const extension = mediaRecorder.mimeType.includes('mp4') ? 'mp4' : mediaRecorder.mimeType.includes('ogg') ? 'ogg' : 'webm';
      const blob = new Blob(chunks, { type: mediaRecorder.mimeType || 'audio/webm' });
      const file = new File([blob], `riff-recording.${extension}`, { type: blob.type });
      const transfer = new DataTransfer();
      transfer.items.add(file);
      audioInput.files = transfer.files;
      saveButton.disabled = false;
      statusText.textContent = 'Recording ready';
      saveHint.textContent = 'Your take is attached and ready to save.';
      stream.getTracks().forEach(track => track.stop());
    });

    mediaRecorder.start();
    startedAt = Date.now();
    timer.textContent = '00:00';
    recordToggle.classList.add('recording');
    recordToggle.setAttribute('aria-pressed', 'true');
    recordLabel.textContent = 'Stop recording';
    captureStatus.classList.add('recording');
    statusText.textContent = 'Listening';
    timerInterval = setInterval(() => {
      timer.textContent = formatTime((Date.now() - startedAt) / 1000);
    }, 250);
  } catch (error) {
    statusText.textContent = 'Microphone access was not allowed';
    saveHint.textContent = 'Allow microphone access, then try again.';
  }
}

// Stop the active recording and update the interface timer and button state.
function stopRecording() {
  if (mediaRecorder?.state === 'recording') mediaRecorder.stop();
  clearInterval(timerInterval);
  recordToggle.classList.remove('recording');
  recordToggle.setAttribute('aria-pressed', 'false');
  recordLabel.textContent = 'Record another take';
  captureStatus.classList.remove('recording');
}

// Switch the recording button between starting and stopping a take.
recordToggle.addEventListener('click', () => {
  if (mediaRecorder?.state === 'recording') stopRecording();
  else startRecording();
});

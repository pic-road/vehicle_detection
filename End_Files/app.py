from flask import Flask, render_template, Response, redirect, url_for
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import cv2
from ultralytics import YOLO
from threading import Thread, Lock

app = Flask(__name__)

model = YOLO('best.pt')  # Replace with your trained model path
CAMERA_URL = '.....' # Replace with your IP WEBCAM address-->connected to same wifi


# Stream and recording flags
streaming = True
recording = False
lock = Lock()
video_writer = None

def generate_frames():
    global recording, video_writer

    cap = cv2.VideoCapture(CAMERA_URL, cv2.CAP_FFMPEG)

    if not cap.isOpened():
        print("❌ Failed to connect to the webcam.")
        return

    fourcc = cv2.VideoWriter_fourcc(*'XVID')

    while True:
        with lock:
            if not streaming:
                break

        success, frame = cap.read()
        if not success:
            break

        results = model(frame)
        annotated_frame = results[0].plot()

        if recording:
            if video_writer is None:
                video_writer = cv2.VideoWriter('output.avi', fourcc, 20.0, (annotated_frame.shape[1], annotated_frame.shape[0]))
            video_writer.write(annotated_frame)
        else:
            if video_writer is not None:
                video_writer.release()
                video_writer = None

        ret, buffer = cv2.imencode('.jpg', annotated_frame)
        if not ret:
            continue

        frame_bytes = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

    cap.release()
    if video_writer:
        video_writer.release()
        video_writer = None


@app.route('/')
def index():
    return render_template('index.html', streaming=streaming, recording=recording)

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/toggle_stream')
def toggle_stream():
    global streaming
    with lock:
        streaming = not streaming
    return redirect(url_for('index'))

@app.route('/toggle_recording')
def toggle_recording():
    global recording
    with lock:
        recording = not recording
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)

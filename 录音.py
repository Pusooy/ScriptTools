import tkinter as tk
import sounddevice as sd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from datetime import datetime
import os
import wave
import threading

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


# Set the highest quality for recording
SAMPLE_RATE = 48000  # Sample rate in Hz
CHANNELS = 2  # Stereo
DTYPE = np.int16  # PCM format

# Create a directory for sound files if it does not exist
if not os.path.exists('sound'):
    os.makedirs('sound')

class AudioRecorder:
    def __init__(self):
        self.is_recording = False
        self.frames = []

    def start_recording(self):
        self.frames = []
        self.is_recording = True
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, dtype=DTYPE, callback=self.callback):
            while self.is_recording:
                sd.sleep(1000)  # Keep recording until is_recording is set to False

    def stop_recording(self):
        self.is_recording = False

    def callback(self, indata, frames, time, status):
        if status:
            print(status)
        self.frames.append(indata.copy())

    def save_recording(self):
        filename = datetime.now().strftime('sound/%Y-%m-%d_%H-%M-%S.flac')
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(2)  # 16 bits
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(b''.join(self.frames.copy()))

# Create the GUI
class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.recorder = AudioRecorder()
        self.record_thread = None
        self.waveform_fig, self.ax = plt.subplots()
        self.line, = self.ax.plot([], [], lw=2)
        self.ax.set_ylim(-1, 1)
        self.ax.set_xlim(0, SAMPLE_RATE / 10)
        self.canvas = None

        self.title('Microphone Recorder')
        self.geometry('300x200')

        # Start button
        self.start_button = tk.Button(self, text='Start Recording', command=self.start_recording)
        self.start_button.pack(pady=5)

        # Stop button
        self.stop_button = tk.Button(self, text='Stop Recording', command=self.stop_recording, state=tk.DISABLED)
        self.stop_button.pack(pady=5)

        # Waveform canvas
        self.canvas = FigureCanvasTkAgg(self.waveform_fig, master=self)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=1)
        self.canvas.draw()
        self.ani = animation.FuncAnimation(self.waveform_fig, self.update_waveform, blit=True)

    def start_recording(self):
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.record_thread = threading.Thread(target=self.recorder.start_recording)
        self.record_thread.start()

    def stop_recording(self):
        self.recorder.stop_recording()
        self.record_thread.join()
        self.recorder.save_recording()
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.ani.event_source.stop()  # Stop the animation

    def update_waveform(self, frame):
        if self.recorder.frames:
            current_frame = self.recorder.frames[-1][:, 0]
            self.line.set_data(np.linspace(0, len(current_frame) / SAMPLE_RATE, len(current_frame)), current_frame)
            self.ax.set_xlim(0, len(current_frame) / SAMPLE_RATE)
            self.ax.set_ylim(current_frame.min(), current_frame.max())
            return (self.line,)
        return (self.line,)

    def on_close(self):
        if self.record_thread is not None:
            self.recorder.stop_recording()
            self.record_thread.join()
        self.ani.event_source.stop()  # Stop the animation
        self.destroy()

if __name__ == '__main__':
    app = Application()
    app.protocol("WM_DELETE_WINDOW", app.on_close)  # Handle window close event
    app.mainloop()
import os
import wave
import webrtcvad
import contextlib
import collections
import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
import uart_ctrl

triggered = False
# 存储音频数据的列表
audio_data_list = []

def voice_trigger(sample_duration, sample_rate, sample_format):
    """
        声音大于阈值trigger_th时, 采集sample_duration(s)的音频
    """
    global triggered
    global audio_data_list

    with sd.InputStream(callback=callback, channels=1, samplerate=sample_rate, dtype=sample_format):
        print("Waiting voice...")
        audio_data = np.array([0])
        
        while(triggered == False):
            if uart_ctrl.return_main_page:
                break

        if uart_ctrl.return_main_page == False:
            # 阻塞等待直到采集完指定时长的音频
            sd.sleep(int(sample_duration * 1000))

            # 将音频数据连接成一个完整的音频
            audio_data = np.concatenate(audio_data_list, axis=0)
            audio_data = np.squeeze(audio_data)

            triggered = False
            audio_data_list = []

        return audio_data


def callback(indata, frames, time, status):
    global triggered
    global audio_data_list

    trigger_th = 0.2
    volume_norm = np.linalg.norm(indata) / 100000

    if volume_norm > trigger_th and triggered == False:
        triggered = True
        print("Voice captured! vol: {}".format(round(volume_norm, 2)))

    if triggered:
        audio_data_list.append(indata.copy())


def VAD(audio, sample_rate, mode):

    audio_chunk_dir = "./my_audios/chunk"

    try:
        # 获取文件夹中的所有文件和子文件夹
        file_list = os.listdir(audio_chunk_dir)

        # 删除文件夹中的每个文件
        for file_name in file_list:
            file_path = os.path.join(audio_chunk_dir, file_name)
            os.remove(file_path)

    except Exception as e:
        print(f"Error while clean '{audio_chunk_dir}' :{e}")

    vad = webrtcvad.Vad(int(mode))
    frames = frame_generator(30, audio, sample_rate)
    frames = list(frames)
    segments = vad_collector(sample_rate, 30, 500, vad, frames)
    segments = list(segments)

    if segments == []:
        print('No audio detected.')
    else:
        for i, segment in enumerate(segments):
            path = './my_audios/chunk/chunk-%002d.wav' % (i,)
            print('Writing %s' % (path,))
            write_wave(path, segment, sample_rate)


class Frame(object):
    """Represents a "frame" of audio data."""
    def __init__(self, bytes, timestamp, duration):
        self.bytes = bytes
        self.timestamp = timestamp
        self.duration = duration


def frame_generator(frame_duration_ms, audio, sample_rate):
    """Generates audio frames from PCM audio data.

    Takes the desired frame duration in milliseconds, the PCM data, and
    the sample rate.

    Yields Frames of the requested duration.
    """
    n = int(sample_rate * (frame_duration_ms / 1000.0) * 2)
    offset = 0
    timestamp = 0.0
    duration = (float(n) / sample_rate) / 2.0
    while offset + n < len(audio):
        yield Frame(audio[offset:offset + n], timestamp, duration)
        timestamp += duration
        offset += n


def vad_collector(sample_rate, frame_duration_ms,
                  padding_duration_ms, vad, frames):
    """Filters out non-voiced audio frames.

    Given a webrtcvad.Vad and a source of audio frames, yields only
    the voiced audio.

    Uses a padded, sliding window algorithm over the audio frames.
    When more than 90% of the frames in the window are voiced (as
    reported by the VAD), the collector triggers and begins yielding
    audio frames. Then the collector waits until 90% of the frames in
    the window are unvoiced to detrigger.

    The window is padded at the front and back to provide a small
    amount of silence or the beginnings/endings of speech around the
    voiced frames.

    Arguments:

    sample_rate - The audio sample rate, in Hz.
    frame_duration_ms - The frame duration in milliseconds.
    padding_duration_ms - The amount to pad the window, in milliseconds.
    vad - An instance of webrtcvad.Vad.
    frames - a source of audio frames (sequence or generator).

    Returns: A generator that yields PCM audio data.
    """
    num_padding_frames = int(padding_duration_ms / frame_duration_ms)
    # We use a deque for our sliding window/ring buffer.
    ring_buffer = collections.deque(maxlen=num_padding_frames)
    # We have two states: TRIGGERED and NOTTRIGGERED. We start in the
    # NOTTRIGGERED state.
    triggered = False

    voiced_frames = []
    for frame in frames:
        is_speech = vad.is_speech(frame.bytes, sample_rate)

        # sys.stdout.write('1' if is_speech else '0')
        if not triggered:
            ring_buffer.append((frame, is_speech))
            num_voiced = len([f for f, speech in ring_buffer if speech])
            # If we're NOTTRIGGERED and more than 90% of the frames in
            # the ring buffer are voiced frames, then enter the
            # TRIGGERED state.
            if num_voiced > 0.9 * ring_buffer.maxlen:
                triggered = True
                # sys.stdout.write('+(%s)' % (ring_buffer[0][0].timestamp,))
                # We want to yield all the audio we see from now until
                # we are NOTTRIGGERED, but we have to start with the
                # audio that's already in the ring buffer.
                for f, s in ring_buffer:
                    voiced_frames.append(f)
                ring_buffer.clear()
        else:
            # We're in the TRIGGERED state, so collect the audio data
            # and add it to the ring buffer.
            voiced_frames.append(frame)
            ring_buffer.append((frame, is_speech))
            num_unvoiced = len([f for f, speech in ring_buffer if not speech])
            # If more than 90% of the frames in the ring buffer are
            # unvoiced, then enter NOTTRIGGERED and yield whatever
            # audio we've collected.
            if num_unvoiced > 0.9 * ring_buffer.maxlen:
                # sys.stdout.write('-(%s)' % (frame.timestamp + frame.duration))
                triggered = False
                yield b''.join([f.bytes for f in voiced_frames])
                ring_buffer.clear()
                voiced_frames = []
    if triggered:
        # sys.stdout.write('-(%s)' % (frame.timestamp + frame.duration))
        pass
    # sys.stdout.write('\n')
    # If we have any leftover voiced audio when we run out of input,
    # yield it.
    if voiced_frames:
        yield b''.join([f.bytes for f in voiced_frames])


def write_wave(path, audio, sample_rate):
    """Writes a .wav file.

    Takes path, PCM audio data, and sample rate.
    """
    with contextlib.closing(wave.open(path, 'wb')) as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio)


if __name__ == "__main__":

    # 配置采样参数
    triggered = False
    trigger_th = 0.5
    sample_duration = 3
    sample_rate = 18000
    sample_format = "int16"
    # 存储音频数据的列表
    audio_data_list = []

    audio_data = voice_trigger(sample_duration, sample_rate, sample_format)

    # 将音频数据保存为.wav文件
    write('output.wav', sample_rate, np.array(audio_data))

    print(f"音频采集完成，保存为 output.wav 文件。")

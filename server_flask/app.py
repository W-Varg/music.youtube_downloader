import os
import re
import sys
import threading
from flask import Flask, request, jsonify, send_from_directory
from pytube import YouTube, Playlist
from flask_cors import CORS
from moviepy.editor import VideoFileClip

app = Flask(__name__)
CORS(app)


def download_video(link, savePath):
    os.makedirs('media/videos', exist_ok=True)

    yt = YouTube(link)

    # Combine title and author to create the filename
    author = yt.author
    title = textSanitizer(yt.title)
    audioName = textSanitizer(f"{author} - {title}") + '.mp3'
    videoName = textSanitizer(f"{author} - {title}") + '.mp4'

    counter = 1
    while os.path.exists(os.path.join('media/videos', videoName)):
        counter += 1
        videoName = textSanitizer(f"{title} ({counter})") + '.mp4'

    def download_in_thread():
        nonlocal videoName
        try:
            videoStream = yt.streams.get_highest_resolution()
            videoStream.download('media/videos', videoName)

            video = VideoFileClip(os.path.join('media/videos', videoName))
            audio = video.audio

            audioFileName = os.path.join(savePath, audioName)
            audio.write_audiofile(audioFileName)

            video.close()

            print(f"🎶 Successful: {audioName}")
        except Exception as e:
            print(f"Error downloading video: {e}")

    # Ejecuta la descarga en un hilo separado
    thread = threading.Thread(target=download_in_thread)
    thread.start()

    return {
        'audioName': audioName,
        'mimeType': 'audio/mpeg',
    }


def download_playlist(playlist_link: str, savePath: str):
    playlist = Playlist(playlist_link)

    counter = 0
    threads = []

    for link in playlist:
        try:
            thread = threading.Thread(
                target=download_video, args=(link, savePath))
            threads.append(thread)
            thread.start()
            counter += 1
        except Exception as e:
            print(f"Error downloading video: {e}")

    # Espera a que todos los hilos terminen antes de continuar
    for thread in threads:
        thread.join()

    return counter


@app.route('/media/<path:filename>', methods=['GET'])
def serve_media(filename):
    return send_from_directory('media', filename)


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        data = request.get_json()
        link = data.get('youtubeURL')
        savePath = data.get('directory') or 'media'

        try:
            if 'playlist' in link.lower():
                totalSuccessfulDownloads = download_playlist(link, savePath)
                message = f'🎶 Downloaded Playlist!, Successful = {totalSuccessfulDownloads}'
            else:
                result = download_video(link, savePath)
                message = '🎶 Successful: ' + result["audioName"]
                # return jsonify(result)

            print(message)
            response = {
                'status': 'Success',
                'message': message,
            }
            return jsonify(response)
        except Exception as e:
            response = {
                'status': 'Error',
                'message': f'An error occurred: {e}',
            }
            return jsonify(response)
    else:
        return jsonify(message="Servicio de descarga y conversion de music.youtube.com")


def clean(videoFileName):
    os.remove(os.path.join('media', videoFileName))


def textSanitizer(title):
    sanitized_text = re.sub(r'[\\\/\'!?\¿¿"$%.\[\]]', '', title)
    sanitized_text = re.sub(r'\s+', ' ', sanitized_text)
    sanitized_text = sanitized_text.strip()
    return sanitized_text


if __name__ == '__main__':
    # Get the IP address and port from the command-line argument
    if len(sys.argv) > 1:
        address = sys.argv[1]
        ip, port = address.split(':')
        port = int(port)
    else:
        ip = '0.0.0.0'
        port = 5000
    app.run(host=ip, port=port, debug=True)

# example run server
# python3 app.py 172.27.39.12:5000

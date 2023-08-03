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


def download_video(link, directorio_video, only_video=False, is_playlist=False):
    os.makedirs('media/videos', exist_ok=True)

    yt = YouTube(link)
    author = yt.author
    title = textSanitizer(yt.title)
    # Combine title and author to create the filename
    audioName = textSanitizer(f"{author} - {title}") + '.mp3'
    videoName = textSanitizer(f"{author} - {title}") + '.mp4'

    counter = 1
    while os.path.exists(os.path.join(directorio_video, videoName)):
        counter += 1
        videoName = textSanitizer(f"{title} ({counter})") + '.mp4'

    def download_in_thread():
        nonlocal videoName, audioName
        try:
            videoStream = yt.streams.get_highest_resolution()
            if is_playlist:
                if only_video:
                    videoStream.download(directorio_video, videoName)
                    return f"🎶 Successful: {videoName}"
                else:
                    ultimo_nombre = os.path.basename(directorio_video)
                    videoStream.download(os.path.join('media/videos', ultimo_nombre), videoName)
                    video = VideoFileClip(os.path.join('media/videos', ultimo_nombre, videoName))
                    audio = video.audio

                    audioFileName = os.path.join(directorio_video, audioName)
                    audio.write_audiofile(audioFileName)
                    video.close()
                    return f"🎶 Successful: {audioName}"
            else:
                if only_video:
                    videoStream.download(directorio_video, videoName)
                    return f"🎶 Successful: {videoName}"
                else:
                    videoStream.download(os.path.join('media/videos'), videoName)
                    video = VideoFileClip(os.path.join('media/videos', videoName))
                    audio = video.audio

                    audioFileName = os.path.join(directorio_video, audioName)
                    audio.write_audiofile(audioFileName)
                    video.close()
                    return f"🎶 Successful: {audioName}"

        except Exception as e:
            print(f"Error downloading video: {e}")
            return None

    # Ejecuta la descarga en un hilo separado
    thread = threading.Thread(target=download_in_thread)
    thread.start()

    return {
        'audioName': audioName,
        'videoName': videoName,
        'mimeType': 'video/mp4' if only_video else 'video/mpeg',
    }


def download_playlist(playlist_link: str, savePath: str, only_video=False):
    playlist = Playlist(playlist_link)
    playlist_folder_name = textSanitizer(playlist.title)  # Nombre de la playlist
    # Crea la carpeta de la playlist
    playlistPath = os.path.join(savePath, playlist_folder_name)
    os.makedirs(playlistPath, exist_ok=True)  # Crea la carpeta de la playlist

    counter = 0
    threads = []

    for link in playlist:
        try:
            thread = threading.Thread(target=download_video, args=(
                link, playlistPath, only_video, True))
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
        is_playlist = 'playlist' in link.lower()
        only_video = data.get('onlyVideo', False)

        try:
            if is_playlist:
                total_downloaded = download_playlist(link, savePath, only_video)
                message = f'🎶 Downloaded Playlist!, Successful = {total_downloaded}'
            else:
                result = download_video(link, savePath, only_video)
                if result is None:
                    message = '🛑 Error downloading the video.'
                else:
                    message = '🎶 Successful: ' + \
                        result['videoName'] if only_video else result['audioName']

            print(message)
            response = {
                'status': 'Success',
                'message': message,
            }
            return jsonify(response)
        except Exception as e:
            response = {'status': 'Error', 'message': f'An error occurred: {e}', }
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

# Cuando la "link" sea una playlist y soloVideo=True, se creará un folder con el nombre de la playlist en el directorio enviado desde el frontend. Los videos se descargan en esa carpeta, y no se extraen los audios.

# Cuando la "link" sea una playlist y soloVideo=False, se creará un folder con el nombre de la playlist en el directorio enviado desde el frontend. Los videos se descargan en la carpeta "media/videos", y los audios se extraen en el folder recién creado.

# Cuando la "link" no sea una playlist y soloVideo=True, el video se descargará dentro del directorio enviado desde el frontend.

# Cuando la "link" no sea una playlist y soloVideo=False, el video se descargará dentro de la carpeta "media/videos", y el audio se extraerá dentro del directorio enviado desde el frontend.

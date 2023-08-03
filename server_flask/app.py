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


def clean(video_file_name):
    os.remove(os.path.join('media', video_file_name))


def text_sanitizer(title):
    sanitized_text = re.sub(r'[\\\/\'!?\¿¿"$:%.\[\]]', '', title)
    sanitized_text = re.sub(r'\s+', ' ', sanitized_text)
    sanitized_text = sanitized_text.strip()
    return sanitized_text


def download_video(link, video_directory, only_video=False, is_playlist=False):
    os.makedirs('media/videos', exist_ok=True)

    yt = YouTube(link)
    author = yt.author
    title = text_sanitizer(yt.title)
    # Combine title and author to create the filename
    audio_name = text_sanitizer(f"{author} - {title}") + '.mp3'
    video_name = text_sanitizer(f"{author} - {title}") + '.mp4'

    counter = 1
    while os.path.exists(os.path.join(video_directory, video_name)):
        counter += 1
        video_name = text_sanitizer(f"{title} ({counter})") + '.mp4'

    def download_in_thread():
        nonlocal video_name, audio_name
        try:
            video_stream = yt.streams.get_highest_resolution()
            if is_playlist:
                if only_video:
                    video_stream.download(video_directory, video_name)
                    return f"� Successful: {video_name}"
                else:
                    ultimo_nombre = os.path.basename(video_directory)
                    video_stream.download(os.path.join('media/videos', ultimo_nombre), video_name)
                    video = VideoFileClip(os.path.join('media/videos', ultimo_nombre, video_name))
                    audio = video.audio

                    audio_file_name = os.path.join(video_directory, audio_name)
                    audio.write_audiofile(audio_file_name)
                    video.close()
                    return f"🎶 Successful: {audio_name}"
            else:
                if only_video:
                    video_stream.download(video_directory, video_name)
                    return f"🎶 Successful: {video_name}"
                else:
                    video_stream.download(os.path.join('media/videos'), video_name)
                    video = VideoFileClip(os.path.join('media/videos', video_name))
                    audio = video.audio

                    audio_file_name = os.path.join(video_directory, audio_name)
                    audio.write_audiofile(audio_file_name)
                    video.close()
                    return f"🎶 Successful: {audio_name}"

        except Exception as e:
            print(f"Error downloading video: {e}")
            return None

    # Ejecuta la descarga en un hilo separado
    thread = threading.Thread(target=download_in_thread)
    thread.start()

    return {
        'audioName': audio_name,
        'videoName': video_name,
        'mimeType': 'video/mp4' if only_video else 'video/mpeg',
    }


def download_playlist(playlist_link: str, save_path: str, only_video=False):
    playlist = Playlist(playlist_link)
    playlist_folder_name = text_sanitizer(playlist.title)  # Nombre de la playlist
    # Crea la carpeta de la playlist
    playlist_path = os.path.join(save_path, playlist_folder_name)
    os.makedirs(playlist_path, exist_ok=True)  # Crea la carpeta de la playlist

    counter = 0
    threads = []

    for link in playlist:
        try:
            thread = threading.Thread(target=download_video, args=(
                link, playlist_path, only_video, True))
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
        save_path = data.get('directory') or 'media'
        is_playlist = 'playlist' in link.lower()
        only_video = data.get('onlyVideo', False)

        try:
            if is_playlist:
                total_downloaded = download_playlist(link, save_path, only_video)
                message = f'🎶 Downloaded Playlist!, Successful = {total_downloaded}'
            else:
                result = download_video(link, save_path, only_video)
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
        return jsonify(message="Servicio de descarga y conversión de music.youtube.com")


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

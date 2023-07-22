import os
import re
import sys
from flask import Flask, request, jsonify
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
    title = nameConverter(yt.title)
    audioName = nameConverter(f"{author} - {title}") + '.mp3'
    videoName = nameConverter(f"{author} - {title}") + '.mp4'
    
    counter = 1
    while os.path.exists(os.path.join('media/videos', videoName)):
        counter += 1
        videoName = nameConverter(f"{title} ({counter})") + '.mp4'

    # Descargar y guarda el archivo de video
    videoStream = yt.streams.get_highest_resolution()
    videoStream.download('media/videos', videoName)

    # Cargar el video descargado y extrae el audio
    video = VideoFileClip(os.path.join('media/videos', videoName))
    audio = video.audio

    # Guardar el archivo de audio en el directorio "savePath"
    audioFileName = os.path.join(savePath, audioName)
    audio.write_audiofile(audioFileName)

    # Eliminar el video descargado y limpia la memoria
    # clean(videoName)
    video.close()

    return audioName


def download_playlist(playlist_link: str, savePath: str):
    playlist = Playlist(playlist_link)

    for link in playlist:
        try:
            download_video(link, savePath)
        except Exception as e:
            print(f"Error downloading video: {e}")


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        data = request.get_json()
        link = data.get('link')
        savePath = data.get('directory') or 'media'

        try:
            if 'playlist' in link.lower():
                download_playlist(link, savePath)
                message = '🎶 Successful Downloaded Playlist!'
            else:
                download_video(link, savePath)
                message = '🎶 Successful Downloaded Video!'

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


def nameConverter(title):
    # Remover espacios dobles
    title = re.sub(r'\s+', ' ', title)
    special_characters = ['°', '|', '/', '?', '*', '"']

    # Remover caracteres especiales usando una expresión regular
    special_characters_regex = '|'.join(map(re.escape, special_characters))
    title = re.sub(rf'[^\w\s{special_characters_regex}-]', '', title)

    return title


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

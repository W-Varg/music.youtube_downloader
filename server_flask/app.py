import os
import re
from flask import Flask, request, jsonify
from pytube import YouTube, Playlist
from flask_cors import CORS
from moviepy.editor import VideoFileClip

app = Flask(__name__)
CORS(app)


def download_video(link, savePath):
    yt = YouTube(link)
    author = yt.author
    title = yt.title

    counter = 1
    while os.path.exists(os.path.join('media', f'archivo{counter}.mp4')):
        counter += 1
    videoFileName = f'archivo{counter}.mp4'

    # Descargar y guarda el archivo de video
    videoStream = yt.streams.get_highest_resolution()
    videoStream.download('media', videoFileName)

    # Cargar el video descargado y extrae el audio
    video = VideoFileClip(os.path.join('media', videoFileName))
    audio = video.audio

    # Combine title and author to create the filename
    filename = nameConverter(f"{author} - {title}") + '.mp3'
    # Guardar el archivo de audio en el directorio "savePath"
    audioFileName = os.path.join(savePath, filename)
    audio.write_audiofile(audioFileName)

    # Eliminar el video descargado y limpia la memoria
    clean(videoFileName)
    video.close()

    return filename


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
        savePath = data.get('directory')

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
    app.run(debug=False)

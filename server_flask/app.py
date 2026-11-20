import glob
import os
import re
import shutil
import sys
import threading
import uuid
from datetime import datetime, timezone
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import yt_dlp

try:
    import imageio_ffmpeg
except ImportError:
    imageio_ffmpeg = None

app = Flask(__name__)
CORS(app)

DOWNLOADS = {}
CANCEL_EVENTS = {}
DOWNLOADS_LOCK = threading.Lock()


class DownloadCancelled(Exception):
    pass


def get_ffmpeg_location():
    system_ffmpeg = shutil.which('ffmpeg')
    if system_ffmpeg:
        return system_ffmpeg
    if imageio_ffmpeg is not None:
        return imageio_ffmpeg.get_ffmpeg_exe()
    return None


def text_sanitizer(title):
    sanitized_text = re.sub(r'[\\\/\'!?\¿"$:%.\[\]\*<>|]', '', title or '')
    sanitized_text = re.sub(r'\s+', ' ', sanitized_text)
    return sanitized_text.strip() or 'untitled'


def register_job(title, job_type, directory):
    job_id = uuid.uuid4().hex[:8]
    cancel_event = threading.Event()
    job = {
        'id': job_id,
        'title': title,
        'type': job_type,
        'directory': directory,
        'status': 'queued',
        'percent': 0.0,
        'downloaded_bytes': 0,
        'total_bytes': None,
        'speed': None,
        'eta': None,
        'message': 'Iniciando...',
        'created_at': datetime.now(timezone.utc).isoformat(),
    }
    with DOWNLOADS_LOCK:
        DOWNLOADS[job_id] = job
        CANCEL_EVENTS[job_id] = cancel_event
    return job_id, cancel_event


def update_job(job_id, **fields):
    with DOWNLOADS_LOCK:
        if job_id in DOWNLOADS:
            DOWNLOADS[job_id].update(fields)


def cleanup_partial_files(directory, tracked_files, stem=None):
    candidates = set()
    for path in tracked_files:
        if path:
            candidates.add(path)
            candidates.add(f"{path}.part")
            candidates.add(f"{path}.ytdl")
            for extra in glob.glob(f"{path}.*"):
                if extra.endswith(('.part', '.ytdl', '.temp')):
                    candidates.add(extra)

    if stem and directory:
        for extra in glob.glob(os.path.join(directory, f"{glob.escape(stem)}*")):
            if extra.endswith(('.part', '.ytdl', '.temp')) or re.search(r'\.f\d+\.[a-z0-9]+$', extra):
                candidates.add(extra)

    for path in candidates:
        try:
            if os.path.isfile(path):
                os.remove(path)
        except OSError:
            pass


def build_ydl_opts(output_template, job_id, cancel_event, tracked_files, only_video=False, is_playlist=False):
    def progress_hook(d):
        if cancel_event.is_set():
            raise DownloadCancelled('Descarga cancelada por el usuario')

        filename = d.get('filename')
        if filename:
            tracked_files.add(filename)

        status = d.get('status')
        if status == 'downloading':
            downloaded = d.get('downloaded_bytes') or 0
            total = d.get('total_bytes') or d.get('total_bytes_estimate')
            percent = round((downloaded / total) * 100, 1) if total else 0.0
            update_job(
                job_id,
                status='downloading',
                downloaded_bytes=downloaded,
                total_bytes=total,
                percent=percent,
                speed=d.get('speed'),
                eta=d.get('eta'),
                message='Descargando...',
            )
        elif status == 'finished':
            update_job(
                job_id,
                status='processing',
                percent=100.0,
                speed=None,
                eta=0,
                message='Procesando / convirtiendo...',
            )

    def postprocessor_hook(d):
        if cancel_event.is_set():
            raise DownloadCancelled('Descarga cancelada por el usuario')

    opts = {
        'outtmpl': output_template,
        'noplaylist': not is_playlist,
        'ignoreerrors': is_playlist,
        'quiet': True,
        'no_warnings': True,
        'noprogress': True,
        'progress_hooks': [progress_hook],
        'postprocessor_hooks': [postprocessor_hook],
    }

    ffmpeg_path = get_ffmpeg_location()
    if ffmpeg_path:
        opts['ffmpeg_location'] = ffmpeg_path

    if only_video:
        opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
        opts['merge_output_format'] = 'mp4'
    else:
        opts['format'] = 'bestaudio/best'
        opts['postprocessors'] = [
            {
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }
        ]

    return opts


def download_video(link, video_directory, only_video=False):
    os.makedirs(video_directory, exist_ok=True)

    extract_opts = {
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
    }
    with yt_dlp.YoutubeDL(extract_opts) as ydl:
        info = ydl.extract_info(link, download=False)

    author = info.get('artist') or info.get('uploader') or info.get('channel') or 'Unknown'
    title = info.get('title') or 'untitled'
    base_name = text_sanitizer(f"{author} - {title}")

    ext = 'mp4' if only_video else 'mp3'
    target_name = f"{base_name}.{ext}"

    counter = 1
    while os.path.exists(os.path.join(video_directory, target_name)):
        counter += 1
        target_name = f"{base_name} ({counter}).{ext}"

    stem = os.path.splitext(target_name)[0]
    output_template = os.path.join(video_directory, f"{stem}.%(ext)s")

    job_id, cancel_event = register_job(
        title=target_name,
        job_type='video' if only_video else 'audio',
        directory=video_directory,
    )
    tracked_files = set()
    ydl_opts = build_ydl_opts(
        output_template,
        job_id,
        cancel_event,
        tracked_files,
        only_video=only_video,
        is_playlist=False,
    )

    def download_in_thread():
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([link])
            if cancel_event.is_set():
                raise DownloadCancelled('Descarga cancelada por el usuario')
            update_job(
                job_id,
                status='completed',
                percent=100.0,
                speed=None,
                eta=0,
                message='Completado',
            )
            print(f"🎶 Successful: {target_name}")
        except DownloadCancelled:
            cleanup_partial_files(video_directory, tracked_files, stem=stem)
            update_job(
                job_id,
                status='cancelled',
                speed=None,
                eta=None,
                message='Cancelado por el usuario',
            )
            print(f"🛑 Cancelled: {target_name}")
        except Exception as e:
            if cancel_event.is_set():
                cleanup_partial_files(video_directory, tracked_files, stem=stem)
                update_job(
                    job_id,
                    status='cancelled',
                    speed=None,
                    eta=None,
                    message='Cancelado por el usuario',
                )
            else:
                update_job(
                    job_id,
                    status='error',
                    speed=None,
                    eta=None,
                    message=str(e),
                )
                print(f"Error downloading video: {e}")

    thread = threading.Thread(target=download_in_thread, daemon=True)
    thread.start()

    return {
        'jobId': job_id,
        'audioName': target_name if not only_video else f"{stem}.mp3",
        'videoName': target_name if only_video else f"{stem}.mp4",
        'mimeType': 'video/mp4' if only_video else 'audio/mpeg',
    }


def download_playlist(playlist_link: str, save_path: str, only_video=False):
    extract_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
    }
    with yt_dlp.YoutubeDL(extract_opts) as ydl:
        playlist_info = ydl.extract_info(playlist_link, download=False)

    playlist_title = text_sanitizer(playlist_info.get('title') or 'playlist')
    entries = playlist_info.get('entries') or []
    total_items = len(entries)

    playlist_path = os.path.join(save_path, playlist_title)
    os.makedirs(playlist_path, exist_ok=True)

    job_id, cancel_event = register_job(
        title=f"Playlist: {playlist_title} ({total_items})",
        job_type='playlist',
        directory=playlist_path,
    )
    tracked_files = set()
    output_template = os.path.join(playlist_path, '%(uploader,channel)s - %(title)s.%(ext)s')
    ydl_opts = build_ydl_opts(
        output_template,
        job_id,
        cancel_event,
        tracked_files,
        only_video=only_video,
        is_playlist=True,
    )

    def download_in_thread():
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([playlist_link])
            if cancel_event.is_set():
                raise DownloadCancelled('Descarga cancelada por el usuario')
            update_job(
                job_id,
                status='completed',
                percent=100.0,
                speed=None,
                eta=0,
                message=f'Playlist completada ({total_items} elementos)',
            )
            print(f"🎶 Playlist finished: {playlist_title} ({total_items} items)")
        except DownloadCancelled:
            cleanup_partial_files(playlist_path, tracked_files)
            update_job(
                job_id,
                status='cancelled',
                speed=None,
                eta=None,
                message='Cancelado por el usuario',
            )
            print(f"🛑 Playlist cancelled: {playlist_title}")
        except Exception as e:
            if cancel_event.is_set():
                cleanup_partial_files(playlist_path, tracked_files)
                update_job(
                    job_id,
                    status='cancelled',
                    speed=None,
                    eta=None,
                    message='Cancelado por el usuario',
                )
            else:
                update_job(
                    job_id,
                    status='error',
                    speed=None,
                    eta=None,
                    message=str(e),
                )
                print(f"Error downloading playlist: {e}")

    thread = threading.Thread(target=download_in_thread, daemon=True)
    thread.start()

    return total_items, job_id


@app.route('/media/<path:filename>', methods=['GET'])
def serve_media(filename):
    return send_from_directory('media', filename)


@app.route('/downloads', methods=['GET'])
def list_downloads():
    with DOWNLOADS_LOCK:
        items = sorted(
            DOWNLOADS.values(),
            key=lambda item: item['created_at'],
            reverse=True,
        )
    return jsonify({'downloads': items}), 200


@app.route('/downloads/<job_id>/cancel', methods=['POST'])
def cancel_download(job_id):
    with DOWNLOADS_LOCK:
        job = DOWNLOADS.get(job_id)
        cancel_event = CANCEL_EVENTS.get(job_id)
        if not job or not cancel_event:
            return jsonify({'status': 'Error', 'message': 'Descarga no encontrada.'}), 404

        if job['status'] in ('completed', 'cancelled', 'error'):
            return jsonify({'status': 'Success', 'message': 'La descarga ya finalizó.', 'job': job}), 200

        cancel_event.set()
        job['status'] = 'cancelling'
        job['message'] = 'Cancelando...'
        snapshot = dict(job)

    return jsonify({'status': 'Success', 'message': 'Cancelación solicitada.', 'job': snapshot}), 200


@app.route('/downloads/clear', methods=['POST'])
def clear_downloads():
    with DOWNLOADS_LOCK:
        removable = [
            jid for jid, job in DOWNLOADS.items()
            if job['status'] in ('completed', 'cancelled', 'error')
        ]
        for jid in removable:
            DOWNLOADS.pop(jid, None)
            CANCEL_EVENTS.pop(jid, None)
    return jsonify({'status': 'Success', 'removed': len(removable)}), 200


@app.route('/', methods=['POST'])
def index():
    data = request.get_json(silent=True) or {}
    link = (data.get('youtubeURL') or data.get('link') or '').strip()
    if not link:
        return jsonify({'status': 'Error', 'message': 'Falta el parámetro youtubeURL.'}), 400

    save_path = (data.get('directory') or '').strip() or 'media'
    is_playlist = 'playlist' in link.lower()
    only_video = bool(data.get('onlyVideo', False))

    try:
        if is_playlist:
            total_downloaded, job_id = download_playlist(link, save_path, only_video)
            message = f'🎶 Descargando playlist ({total_downloaded} elementos)...'
        else:
            result = download_video(link, save_path, only_video)
            job_id = result['jobId']
            filename = result['videoName'] if only_video else result['audioName']
            message = f'🎶 Descargando: {filename}'

        print(message)
        return jsonify({'status': 'Success', 'message': message, 'jobId': job_id})
    except Exception as e:
        print(f"Error handling request: {e}")
        return jsonify({'status': 'Error', 'message': f'An error occurred: {e}'})


@app.route('/', methods=['GET'])
def index_get():
    return jsonify(
        status='ok',
        message='Servicio de descarga y conversión de music.youtube.com',
        endpoints={
            'health': '/health',
            'info': '/info',
            'downloads': 'GET /downloads',
            'cancel': 'POST /downloads/<job_id>/cancel',
            'clear': 'POST /downloads/clear',
            'download': 'POST /',
            'media': '/media/<filename>',
        },
    )


@app.route('/health', methods=['GET'])
def health():
    return jsonify(
        status='ok',
        service='audio_downloader',
        ffmpeg_available=get_ffmpeg_location() is not None,
        timestamp=datetime.now(timezone.utc).isoformat(),
    ), 200


@app.route('/info', methods=['GET'])
def info():
    return jsonify(
        status='ok',
        service='audio_downloader',
        engine='yt-dlp',
        yt_dlp_version=yt_dlp.version.__version__,
        ffmpeg_available=get_ffmpeg_location() is not None,
        description='Servicio de descarga y conversión de YouTube y YouTube Music',
        default_directory='media',
        python_version=sys.version.split()[0],
        endpoints={
            'GET /': 'Estado básico y lista de endpoints',
            'GET /health': 'Verificación de salud del servidor',
            'GET /info': 'Información detallada del servicio',
            'GET /downloads': 'Listado en tiempo real de descargas',
            'POST /downloads/<job_id>/cancel': 'Cancelar una descarga activa',
            'POST /downloads/clear': 'Limpiar descargas finalizadas/canceladas',
            'POST /': 'Descargar audio (.mp3) o video (.mp4) / playlist',
            'GET /media/<filename>': 'Servir archivo descargado',
        },
    ), 200


if __name__ == '__main__':
    # Get the IP address and port from the command-line argument
    if len(sys.argv) > 1:
        address = sys.argv[1]
        ip, port = address.split(':')
        port = int(port)
    else:
        ip = '0.0.0.0'
        port = 6001
    app.run(host=ip, port=port, debug=True)

# example run server
# python3 app.py 172.27.39.12:6001

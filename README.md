# Audio & Video Downloader (Flask + Extensión de Navegador)

Aplicación compuesta por un servidor backend en **Python (Flask)** y una **extensión para navegadores basados en Chromium** (Chrome, Brave, Edge) que permite descargar audio (`.mp3`) o video (`.mp4`) desde **YouTube** y **YouTube Music**, incluyendo videos individuales y playlists completas.

## Estructura del proyecto

```text
audio_downloader/
├── chrome_extension/       # Extensión de navegador (Manifest V3)
│   ├── manifest.json
│   ├── popup.html          # Interfaz de la extensión
│   ├── popup.js            # Lógica y petición al servidor Flask
│   ├── popup.css
│   └── background.js       # Service worker (notificaciones y descargas)
├── server_flask/           # Servidor backend en Flask
│   ├── app.py              # API principal y lógica de descarga/conversión
│   ├── requirements.txt    # Dependencias de Python
│   ├── run_app.sh          # Script para levantar el servidor con Gunicorn
│   └── request.http        # Ejemplos de peticiones HTTP
└── README.md
```

---

## Requisitos previos

- **Python 3.10+** y `pip`
- **Git**
- Navegador basado en Chromium (**Google Chrome**, **Brave**, **Microsoft Edge**, etc.)

---

## Instalación desde cero

### 1. Clonar el repositorio

```bash
git clone https://github.com/W-Varg/music.youtube_downloader.git
cd music.youtube_downloader/server_flask
```

### 2. Crear el entorno virtual (`venv`)

En **Linux / macOS**:

```bash
python3 -m venv env
```

> Si no tienes `venv` instalado en Debian/Ubuntu, instálalo con:
> ```bash
> sudo apt install python3-venv
> ```

En **Windows (PowerShell)**:

```powershell
python -m venv env
```

### 3. Activar el entorno virtual

En **Linux / macOS**:

```bash
source env/bin/activate
```

En **Windows (PowerShell)**:

```powershell
.\env\Scripts\Activate.ps1
```

En **Windows (CMD)**:

```cmd
env\Scripts\activate.bat
```

### 4. Instalar las dependencias

Con el entorno virtual activado, instala los paquetes listados en `server_flask/requirements.txt` (`Flask`, `Flask-Cors`, `gunicorn`, `moviepy`, `pytube`):

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Actualizar el proyecto y los paquetes

Para traer los últimos cambios del repositorio y actualizar las dependencias instaladas:

```bash
# 1. Ir a la raíz del repositorio y actualizar el código
git pull

# 2. Entrar al servidor y activar el entorno virtual
cd server_flask
source env/bin/activate   # En Windows PowerShell: .\env\Scripts\Activate.ps1

# 3. Actualizar pip y los paquetes del entorno
pip install --upgrade pip
pip install --upgrade -r requirements.txt
```

> **Nota:** Si YouTube cambia su API y las descargas fallan, actualiza `pytube` manualmente con:
> ```bash
> pip install --upgrade pytube
> ```
> Si hubo cambios en la carpeta `chrome_extension/`, recuerda hacer clic en el botón **Recargar** (↻) de la extensión en `chrome://extensions/` o `brave://extensions/`.

---

## Levantar el servidor

Asegúrate de estar dentro de `server_flask/` con el entorno virtual activado.

### Opción A: Modo desarrollo (Flask)

Inicia el servidor en `0.0.0.0:6000` (accesible desde `127.0.0.1:6000` y tu red local):

```bash
python3 app.py
```

También puedes especificar una IP y puerto concretos como argumento:

```bash
python3 app.py 127.0.0.1:6000
```

### Opción B: Producción con Gunicorn

Usando `gunicorn` directamente:

```bash
gunicorn app:app -b 0.0.0.0:6000 --log-level=error
```

O ejecutando el script incluido (ajusta la IP dentro de `server_flask/run_app.sh` si es necesario):

```bash
chmod +x run_app.sh
./run_app.sh
```

### Verificar que el servidor está activo

```bash
curl http://127.0.0.1:6000/
```

Deberías recibir:

```json
{"message": "Servicio de descarga y conversión de music.youtube.com"}
```

---

## Instalar y configurar la extensión en el navegador

1. Abre la página de extensiones en tu navegador:
   - **Chrome:** `chrome://extensions/`
   - **Brave:** `brave://extensions/`
   - **Edge:** `edge://extensions/`
2. Activa el **Modo desarrollador** (*Developer mode*) en la esquina superior derecha.
3. Haz clic en **Cargar descomprimida** (*Load unpacked*).
4. Selecciona la carpeta `chrome_extension/` del proyecto.
5. (Opcional) Fija la extensión **Audio & Video Downloader** en la barra de herramientas para acceso rápido.

---

## Guía de uso de la extensión

1. **Inicia el servidor Flask** siguiendo los pasos de la sección [Levantar el servidor](#levantar-el-servidor).
2. **Abre YouTube o YouTube Music** en una pestaña del navegador y navega al video, canción o playlist que deseas descargar.
3. **Haz clic en el ícono de la extensión** en la barra del navegador.
4. **Configura y descarga** usando los controles del popup:
   - **Campo `Servidor Flask`:** URL donde corre el servidor (por defecto `http://127.0.0.1:6000`; puedes cambiar el puerto o usar una IP de tu red local, por ejemplo `http://127.0.0.1:6001`). Se guarda automáticamente.
   - **Campo `Directorio de destino`:** Ruta absoluta del servidor donde quieres guardar los archivos (por ejemplo, `/home/usuario/Music`). El valor se guarda automáticamente en el navegador. Si lo dejas vacío, los archivos se guardarán en `server_flask/media/`.
   - **Botón `YT Music` (azul):** Busca la pestaña activa o abierta de `music.youtube.com` y descarga el audio en formato **`.mp3`**.
   - **Botón `YT Audio` (rojo):** Busca la pestaña activa o abierta de `www.youtube.com` y descarga el audio en formato **`.mp3`**.
   - **Botón `YT Video` (verde):** Busca la pestaña activa o abierta de `www.youtube.com` y descarga el video en formato **`.mp4`** (máxima resolución disponible).
   - **Casilla `Devolver Datos`:** Guarda la preferencia y envía `returnData: true` en la petición al servidor.

### Descarga de playlists

Si la pestaña abierta corresponde a una URL de playlist (contiene `playlist` en la dirección), el servidor creará automáticamente una subcarpeta con el nombre de la playlist dentro del directorio indicado y descargará todos sus elementos.

---

## Uso directo de la API (opcional)

También puedes disparar descargas directamente mediante `POST /` sin usar la extensión:

```bash
curl -X POST http://127.0.0.1:6000/ \
  -H "Content-Type: application/json" \
  -d '{
    "youtubeURL": "https://music.youtube.com/watch?v=NjUk5R_DZ7g",
    "directory": "/home/dev/Music",
    "onlyVideo": false
  }'
```

| Parámetro    | Tipo      | Descripción                                                                 |
| ------------ | --------- | --------------------------------------------------------------------------- |
| `youtubeURL` | `string`  | URL del video o playlist de YouTube / YouTube Music (**requerido**).        |
| `directory`  | `string`  | Ruta de destino en el servidor (opcional, por defecto `media`).             |
| `onlyVideo`  | `boolean` | `true` para descargar `.mp4`; `false` para convertir a `.mp3` (por defecto). |

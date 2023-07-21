# Instalación y configuración del entorno

## Paso 1: Clonar el repositorio

git clone <URL_DEL_REPOSITORIO>
cd <NOMBRE_DEL_REPOSITORIO>


# Paso 2: Crear un entorno virtual (venv)
```shell
Copy code
# Si no tienes instalado venv, puedes hacerlo con el siguiente comando:
# En Linux/macOS
python3 -m pip install --user virtualenv

# En Windows (usando PowerShell)
python -m pip install --user virtualenv

# Crear el entorno virtual
# En Linux/macOS
python3 -m venv venv

# En Windows
python -m venv venv
```
# Paso 3: Activar el entorno virtual
En Linux/macOS
```bash
source venv/bin/activate
```
En Windows (usando PowerShell)

```bash
venv\Scripts\Activate.ps1
```

# Paso 4: Instalar las dependencias
```bash
pip install -r requirements.txt
```

Ejecutar el servidor
```bash
python3 app.py
```
# AGREGAR LA EXTENSION EN LA NAVEGADOR

ingresa configuracion del navegador, hacia las entensions
brave://extensions/
- activar el modo desarrollador
- luego cargar paquete o cargar extension, seleccionar el directorio de chrome_extension
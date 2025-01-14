import os
import time
import logging
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from datetime import datetime
import shutil
import threading
import json
import sys
import requests

# Versión actual del programa
VERSION = "1.0.1"
# URL del archivo de versión y del ejecutable actualizado
VERSION_URL = "https://raw.githubusercontent.com/f-capano/HL7SegmentRemover/refs/heads/main/version.txt"  # Reemplázalo con la URL de tu archivo de versión
UPDATE_URL = "https://github.com/f-capano/HL7SegmentRemover/releases/download/v1.0.0/HL7SegmentRemover.exe"  # Reemplázalo con la URL del ejecutable actualizado

# Configuración del logging
logging.basicConfig(
    filename="procesamiento_hl7.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Variables globales
intervalo_actual = 10
procesamiento_activo = False
hilo_procesamiento = None
config_file = "configuracion.json"

# Función para cargar configuraciones
def cargar_configuracion():
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            return json.load(f)
    return {}

# Función para guardar configuraciones
def guardar_configuracion(config):
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=4)

# Función para eliminar el segmento del archivo HL7
def eliminar_segmento(hl7_texto, segmento_a_eliminar):
    lineas = hl7_texto.splitlines()
    lineas_filtradas = [linea for linea in lineas if not linea.startswith(segmento_a_eliminar)]
    return "\n".join(lineas_filtradas)

# Función para mover archivos a la carpeta de backup
def mover_a_backup(archivo_entrada, carpeta_entrada):
    backup_dir = os.path.join(carpeta_entrada, "backup")
    now = datetime.now()
    mes_anio = now.strftime("%B_%Y")  # Ejemplo: "January_2025"
    carpeta_backup_mes = os.path.join(backup_dir, mes_anio)

    if not os.path.exists(carpeta_backup_mes):
        os.makedirs(carpeta_backup_mes)

    archivo_destino = os.path.join(carpeta_backup_mes, os.path.basename(archivo_entrada))
    shutil.move(archivo_entrada, archivo_destino)
    logging.info(f"Archivo movido a backup: {archivo_destino}")

# Función para procesar archivos
def procesar_archivos(directorio_entrada, segmento_a_eliminar, directorio_salida):
    if not os.path.exists(directorio_salida):
        os.makedirs(directorio_salida)
        logging.info(f"Carpeta 'Modified' creada en: {directorio_salida}")

    archivos = [f for f in os.listdir(directorio_entrada) if f.endswith('.hl7')]

    if not archivos:
        logging.warning(f"No se encontraron archivos HL7 en el directorio: {directorio_entrada}")

    for archivo in archivos:
        archivo_entrada = os.path.join(directorio_entrada, archivo)
        try:
            with open(archivo_entrada, 'r') as f:
                hl7_texto = f.read()

            logging.info(f"Procesando archivo: {archivo}")

            hl7_modificado = eliminar_segmento(hl7_texto, segmento_a_eliminar)

            if hl7_texto != hl7_modificado:
                archivo_salida = os.path.join(directorio_salida, archivo)
                with open(archivo_salida, 'w') as f:
                    f.write(hl7_modificado)

                logging.info(f"Archivo modificado y guardado en: {archivo_salida}")
                mover_a_backup(archivo_entrada, directorio_entrada)
            else:
                logging.info(f"El archivo {archivo} no contenía el segmento {segmento_a_eliminar}. No se modificó.")

        except Exception as e:
            logging.error(f"Error al procesar el archivo {archivo}: {e}")

# Función para iniciar el procesamiento automático
def iniciar_proceso_periodico():
    global procesamiento_activo, hilo_procesamiento
    carpeta_entrada = entry_carpeta_entrada.get()
    segmento = entry_segmento.get()

    if not carpeta_entrada or not segmento:
        messagebox.showwarning("Entrada incompleta", "Por favor, selecciona la carpeta de entrada y el segmento a eliminar.")
        return

    carpeta_salida = os.path.join(carpeta_entrada, "Modified")
    procesamiento_activo = True
    actualizar_estado_visual()

    def tarea_periodica():
        while procesamiento_activo:
            procesar_archivos(carpeta_entrada, segmento, carpeta_salida)
            time.sleep(intervalo_actual)

    hilo_procesamiento = threading.Thread(target=tarea_periodica, daemon=True)
    hilo_procesamiento.start()
    messagebox.showinfo("Procesamiento automático", f"Procesamiento iniciado con intervalo de {intervalo_actual} segundos.")

# Función para detener el procesamiento automático
def detener_proceso():
    global procesamiento_activo
    procesamiento_activo = False
    actualizar_estado_visual()
    messagebox.showinfo("Procesamiento detenido", "El procesamiento automático ha sido detenido.")

# Función para actualizar el estado visual
def actualizar_estado_visual():
    if procesamiento_activo:
        estado_label.config(text="Activo", bg="green", fg="white")
    else:
        estado_label.config(text="Detenido", bg="red", fg="white")

# Función para reiniciar el programa
def reiniciar_programa():
    python = sys.executable
    os.execl(python, python, *sys.argv)

# Función para actualizar el intervalo
def actualizar_intervalo():
    global intervalo_actual
    try:
        nuevo_intervalo = int(entry_intervalo.get())
        if nuevo_intervalo > 0:
            intervalo_actual = nuevo_intervalo
            logging.info(f"Intervalo actualizado a: {intervalo_actual} segundos.")
            messagebox.showinfo("Intervalo actualizado", f"Nuevo intervalo: {intervalo_actual} segundos.")
        else:
            messagebox.showwarning("Valor inválido", "El intervalo debe ser mayor a 0.")
    except ValueError:
        messagebox.showerror("Error", "Por favor, ingresa un número válido.")

# Función para seleccionar la carpeta de entrada
def seleccionar_carpeta_entrada():
    carpeta = filedialog.askdirectory(title="Selecciona la carpeta de entrada")
    if carpeta:
        entry_carpeta_entrada.delete(0, tk.END)
        entry_carpeta_entrada.insert(0, carpeta)

# Función para verificar si hay actualizaciones
def verificar_actualizacion():
    try:
        respuesta = requests.get(VERSION_URL)
        if respuesta.status_code == 200:
            ultima_version = respuesta.text.strip()
            if ultima_version != VERSION:
                if messagebox.askyesno(
                    "Actualización disponible",
                    f"Hay una nueva versión disponible ({ultima_version}). ¿Quieres actualizar?"
                ):
                    descargar_actualizacion()
        else:
            logging.warning("No se pudo verificar la versión más reciente.")
    except Exception as e:
        logging.error(f"Error al verificar actualizaciones: {e}")

# Función para descargar la nueva versión
def descargar_actualizacion():
    try:
        respuesta = requests.get(UPDATE_URL, stream=True)
        with open("procesador_hl7_nuevo.exe", "wb") as f:
            for chunk in respuesta.iter_content(chunk_size=8192):
                f.write(chunk)
        messagebox.showinfo(
            "Actualización descargada",
            "La nueva versión se descargó correctamente. Cierra este programa y ejecuta 'procesador_hl7_nuevo.exe'."
        )
    except Exception as e:
        logging.error(f"Error al descargar la actualización: {e}")
        messagebox.showerror("Error", "No se pudo descargar la actualización.")

# Cargar configuraciones al inicio
config = cargar_configuracion()

# Si no hay configuración, pedirla
if not config:
    print("No se encontraron configuraciones previas. Por favor ingresa los datos iniciales.")
    config = {
        'directorio': '',
        'segmento': '',
        'intervalo': 10
    }

# Usar las configuraciones cargadas
entry_carpeta_entrada = tk.Entry(ventana, width=50)
entry_carpeta_entrada.insert(0, config['directorio'])
entry_intervalo = tk.Entry(ventana, width=10)
entry_intervalo.insert(0, str(config['intervalo']))

# Llamar a la función de verificación al iniciar el programa
verificar_actualizacion()

# Crear la ventana principal
ventana = tk.Tk()
ventana.title("Procesador de Archivos HL7")
ventana.geometry("600x500")

# Widgets de la GUI
tk.Label(ventana, text="Carpeta de Entrada:").pack(pady=5)
entry_carpeta_entrada.pack(pady=5)
tk.Button(ventana, text="Seleccionar Carpeta", command=seleccionar_carpeta_entrada).pack(pady=5)

tk.Label(ventana, text="Segmento a Eliminar (Ej. ZAC):").pack(pady=5)
entry_segmento = tk.Entry(ventana, width=50)
entry_segmento.insert(0, config['segmento'])
entry_segmento.pack(pady=5)

tk.Label(ventana, text="Intervalo de procesamiento (segundos):").pack(pady=5)
entry_intervalo.pack(pady=5)

tk.Button(ventana, text="Iniciar Procesamiento Automático", command=iniciar_proceso_periodico).pack(pady=10)
tk.Button(ventana, text="Detener Procesamiento", command=detener_proceso).pack(pady=5)
tk.Button(ventana, text="Reiniciar Programa", command=reiniciar_programa).pack(pady=5)

# Indicador de estado visual
tk.Label(ventana, text="Estado:").pack(pady=5)
estado_label = tk.Label(ventana, text="Detenido", bg="red", fg="white", width=15, height=2)
estado_label.pack(pady=10)

# Área de mensajes de log
log_area = scrolledtext.ScrolledText(ventana, width=70, height=10, wrap=tk.WORD)
log_area.pack(pady=10)

# Función para mostrar logs
def leer_logs():
    with open("procesamiento_hl7.log", "r") as f:
        log_area.delete(1.0, tk.END)
        log_area.insert(tk.END, f.read())

# Leer los logs cada cierto tiempo
ventana.after(1000, leer_logs)

ventana.mainloop()

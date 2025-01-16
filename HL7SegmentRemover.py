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
VERSION_URL = "https://raw.githubusercontent.com/f-capano/HL7SegmentRemover/refs/heads/main/version.txt"
UPDATE_URL = "https://github.com/f-capano/HL7SegmentRemover/releases/download/v1.0.0/HL7SegmentRemover.exe"

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

# Función para actualizar el estado visual
def actualizar_estado_visual():
    if procesamiento_activo:
        estado_label.config(text="Activo", bg="green", fg="white")
    else:
        estado_label.config(text="Detenido", bg="red", fg="white")

# Función para eliminar el segmento del archivo HL7
def eliminar_segmento(hl7_texto, segmento_a_eliminar):
    lineas = hl7_texto.splitlines()
    lineas_filtradas = [linea for linea in lineas if not linea.startswith(segmento_a_eliminar)]
    return "\n".join(lineas_filtradas)

# Función para mover archivos a la carpeta de backup
def mover_a_backup(archivo_entrada, carpeta_entrada):
    backup_dir = os.path.join(carpeta_entrada, "backup")
    now = datetime.now()
    mes_anio = now.strftime("%B_%Y")
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
    global procesamiento_activo, hilo_procesamiento, intervalo_actual
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
            for _ in range(intervalo_actual):
                if not procesamiento_activo:
                    break
                time.sleep(1)

    hilo_procesamiento = threading.Thread(target=tarea_periodica, daemon=True)
    hilo_procesamiento.start()
    guardar_configuracion({'intervalo': intervalo_actual, 'directorio': carpeta_entrada, 'segmento': segmento})
    messagebox.showinfo("Procesamiento automático", f"Procesamiento iniciado con intervalo de {intervalo_actual} segundos.")

# Función para detener el procesamiento automático
def detener_proceso():
    global procesamiento_activo
    procesamiento_activo = False
    actualizar_estado_visual()
    messagebox.showinfo("Procesamiento detenido", "El procesamiento automático ha sido detenido.")

# Carga inicial de configuraciones
config = cargar_configuracion()
carpeta_entrada = config.get('directorio', '')
segmento = config.get('segmento', '')
intervalo_actual = config.get('intervalo', 10)

# Crear la ventana principal
ventana = tk.Tk()
ventana.title("Procesador de Archivos HL7")
ventana.geometry("600x500")

# Widgets de la GUI
tk.Label(ventana, text="Carpeta de Entrada:").pack(pady=5)
entry_carpeta_entrada = tk.Entry(ventana, width=50)
entry_carpeta_entrada.insert(0, carpeta_entrada)
entry_carpeta_entrada.pack(pady=5)
tk.Button(ventana, text="Seleccionar Carpeta", command=lambda: entry_carpeta_entrada.insert(0, filedialog.askdirectory())).pack(pady=5)

tk.Label(ventana, text="Segmento a Eliminar (Ej. ZAC):").pack(pady=5)
entry_segmento = tk.Entry(ventana, width=50)
entry_segmento.insert(0, segmento)
entry_segmento.pack(pady=5)

tk.Label(ventana, text="Intervalo de procesamiento (segundos):").pack(pady=5)
entry_intervalo = tk.Entry(ventana, width=10)
entry_intervalo.insert(0, str(intervalo_actual))
entry_intervalo.pack(pady=5)

tk.Button(ventana, text="Iniciar Procesamiento Automático", command=iniciar_proceso_periodico).pack(pady=10)
tk.Button(ventana, text="Detener Procesamiento", command=detener_proceso).pack(pady=5)

estado_label = tk.Label(ventana, text="Detenido", bg="red", fg="white", width=15, height=2)
estado_label.pack(pady=10)

def guardar_configuracion_al_cerrar():
    guardar_configuracion({
        'directorio': entry_carpeta_entrada.get(),
        'segmento': entry_segmento.get(),
        'intervalo': intervalo_actual
    })
    ventana.destroy()

ventana.protocol("WM_DELETE_WINDOW", guardar_configuracion_al_cerrar)
ventana.mainloop()


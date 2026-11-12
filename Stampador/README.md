# Integración Qt + OPC UA + PLC B&R — Versión 3

## Contenido

- `widget.py`: ventana principal PySide6; conserva los nombres de controles de la interfaz recibida.
- `opcua_manager.py`: cliente OPC UA asíncrono ejecutado en un `QThread`.
- `form.ui`: interfaz original recibida, sin rediseño.
- `requirements.txt`: dependencias Python.

## Instalación

Se recomienda crear un entorno virtual e instalar:

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

## Generar `ui_form.py`

Desde la carpeta del proyecto, ejecuta:

```bash
pyside6-uic form.ui -o ui_form.py
```

También puedes abrir `form.ui` en Qt Designer y regenerar el archivo Python con `pyside6-uic`.

## Ejecutar

```bash
python widget.py
```

## Configuración OPC UA

El endpoint y los NodeIds están definidos al inicio de `opcua_manager.py`. Se conservaron los valores del archivo que proporcionaste:

- Endpoint: `opc.tcp://172.16.1.95:4840`
- Namespace: `6`
- Seguridad/autenticación: se utiliza la configuración anónima predeterminada del servidor, igual que en la implementación recibida.

Si cambia la dirección del PLC o algún NodeId, actualiza `ENDPOINT` o `NODES`.

## Comportamiento de los modos

- **Manual:** el botón envía `manualMode = TRUE` una sola vez. La aplicación no escribe `FALSE`; el PLC debe restablecer la solicitud cuando termine.
- **Automático:** el botón alterna la solicitud mantenida `autoMode` usando el último valor leído del PLC. Se bloquea mientras espera confirmación del valor solicitado.
- **Estado mostrado:** `labelStatusMode` se actualiza con `manualActive` y `autoActive`, no con el resultado de la escritura. Si ambos estados aparecen activos, muestra una condición de error.

## Notas de seguridad y puesta en marcha

1. Mantén enclavamientos, permisos, secuencias y funciones de seguridad en el PLC. La HMI no sustituye la lógica de seguridad.
2. Prueba primero con la máquina en condición segura y observa las variables en UA Expert.
3. La aceptación de una escritura OPC UA confirma que el servidor aceptó el dato; no demuestra por sí sola que la secuencia física haya arrancado.
4. El tiempo de espera de confirmación de `autoMode` es de aproximadamente 5 segundos (10 ciclos de lectura a 500 ms). Puedes ajustar `auto_pending_timeout_cycles` en `widget.py`.
5. `labelMedicionOk` queda reservado para el estado del módulo de medición. El estado de conexión OPC UA se muestra en el título de la ventana para evitar que las lecturas lo sobrescriban.

## Dependencias

Las versiones mínimas están en `requirements.txt`. Si ya tienes un entorno funcional, puedes conservar las versiones que estás usando.

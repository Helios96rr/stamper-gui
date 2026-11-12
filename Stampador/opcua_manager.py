"""Cliente OPC UA asíncrono ejecutado en un QThread."""
import asyncio

from asyncua import Client, ua
from PySide6.QtCore import QThread, Signal

ENDPOINT = "opc.tcp://172.16.1.95:4840"

NODES = {
    # Datos de medición
    "measurement_ok": "ns=6;s=::ModbusTcp:Modbus.measuringStamper.ModuleOk",
    "measurement_digits": "ns=6;s=::ModbusTcp:Modbus.measuringStamper.digits",
    "measurement_class": "ns=6;s=::ModbusTcp:Modbus.measuringStamper.class",
    "measurement_unit": "ns=6;s=::ModbusTcp:Modbus.measuringStamper.unit",
    # Datos de lote
    "batch_ok": "ns=6;s=::ModbusTcp:Modbus.batchStamper.ModuleOk",
    "batch_digits_1": "ns=6;s=::ModbusTcp:Modbus.batchStamper.digits[1]",
    "batch_digits_2": "ns=6;s=::ModbusTcp:Modbus.batchStamper.digits[2]",
    # Barra de sensores
    "sensor_ok": "ns=6;s=::ModbusTcp:Modbus.sensorBar.ModuleOk",
    "sensor_status": "ns=6;s=::ModbusTcp:Modbus.sensorBar.statusSensorBar",
    # Solicitudes de modo
    "manual_mode": "ns=6;s=::ModbusTcp:Modbus.cmd.manualMode",
    "auto_mode": "ns=6;s=::ModbusTcp:Modbus.cmd.autoMode",
    # Confirmaciones de estado
    "manual_active": "ns=6;s=::ModbusTcp:Modbus.status.manualActive",
    "auto_active": "ns=6;s=::ModbusTcp:Modbus.status.autoActive",
}


class OpcUaWorker(QThread):
    data_received = Signal(dict)
    connection_changed = Signal(bool, str)
    write_result = Signal(str, bool, str)

    def __init__(self, endpoint=ENDPOINT, poll_interval=0.5, parent=None):
        super().__init__(parent)
        self.endpoint = endpoint
        self.poll_interval = poll_interval
        self._running = True
        self._loop = None
        self._write_queue = None
        self._stop_event = None

    def run(self):
        asyncio.run(self._main())

    async def _main(self):
        self._loop = asyncio.get_running_loop()
        self._write_queue = asyncio.Queue()
        self._stop_event = asyncio.Event()

        try:
            while self._running:
                try:
                    self.connection_changed.emit(False, "Conectando al PLC...")
                    async with Client(url=self.endpoint) as client:
                        nodes = {
                            key: client.get_node(node_id)
                            for key, node_id in NODES.items()
                        }
                        await self._diagnose_write_nodes(nodes)
                        self.connection_changed.emit(True, "OPC UA conectado")

                        while self._running:
                            await self._process_writes(nodes)
                            values = {}
                            for key, node in nodes.items():
                                try:
                                    values[key] = await node.read_value()
                                except Exception as exc:
                                    values[key] = None
                                    print(f"[OPC UA] Lectura {key}: {exc}")

                            self.data_received.emit(values)
                            if await self._wait_or_stop(self.poll_interval):
                                break

                except Exception as exc:
                    self.connection_changed.emit(
                        False, f"Sin conexión: {exc}. Reintentando..."
                    )
                    if await self._wait_or_stop(2.0):
                        break
        finally:
            self.connection_changed.emit(False, "Cliente OPC UA detenido")
            self._loop = None
            self._write_queue = None
            self._stop_event = None

    async def _diagnose_write_nodes(self, nodes):
        for key in ("manual_mode", "auto_mode"):
            try:
                node = nodes[key]
                variant_type = await node.read_data_type_as_variant_type()
                access = await node.get_user_access_level()
                print(
                    f"[OPC UA] {key}: DataType={variant_type.name}; "
                    f"UserAccessLevel={[item.name for item in access]}"
                )
            except Exception as exc:
                print(f"[OPC UA] Diagnóstico {key}: {exc}")

    async def _process_writes(self, nodes):
        while not self._write_queue.empty():
            key, value = await self._write_queue.get()
            try:
                node = nodes[key]
                variant_type = await node.read_data_type_as_variant_type()
                # Se escribe únicamente Value, sin SourceTimestamp.
                data_value = ua.DataValue(ua.Variant(value, variant_type))
                await node.write_attribute(ua.AttributeIds.Value, data_value)
                self.write_result.emit(
                    key, True, f"Escritura aceptada ({variant_type.name})"
                )
            except Exception as exc:
                self.write_result.emit(key, False, str(exc))
            finally:
                self._write_queue.task_done()

    async def _wait_or_stop(self, seconds):
        if self._stop_event is None:
            await asyncio.sleep(seconds)
            return not self._running
        try:
            await asyncio.wait_for(self._stop_event.wait(), timeout=seconds)
            return True
        except asyncio.TimeoutError:
            return not self._running

    def write_value(self, key, value):
        if key not in ("manual_mode", "auto_mode"):
            self.write_result.emit(key, False, "Nodo no habilitado para escritura")
            return
        if self._loop is None or self._write_queue is None or not self.isRunning():
            self.write_result.emit(key, False, "Cliente OPC UA no iniciado")
            return
        self._loop.call_soon_threadsafe(
            self._write_queue.put_nowait, (key, value)
        )

    def stop(self):
        self._running = False
        if self._loop is not None and self._stop_event is not None:
            self._loop.call_soon_threadsafe(self._stop_event.set)
        if self.isRunning():
            self.wait(5000)

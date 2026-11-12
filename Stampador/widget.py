"""Ventana principal del sistema de estampado."""
import sys

from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import QTimer

from ui_form import Ui_Widget
from opcua_manager import OpcUaWorker


class Widget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_Widget()
        self.ui.setupUi(self)
        self.setWindowTitle("ESTAMPADOR")

        self.opc = OpcUaWorker()
        self.opc.connection_changed.connect(self.on_connection_changed)
        self.opc.data_received.connect(self.on_data_received)
        self.opc.write_result.connect(self.on_write_result)

        self.connected = False
        self.auto_mode_value = None
        self.auto_pending_value = None
        self.auto_pending_cycles = 0
        self.auto_pending_timeout_cycles = 10  # 10 ciclos x 0.5 s = aprox. 5 s

        self.ui.pushBtnManual.setEnabled(False)
        self.ui.pushBtnAuto.setEnabled(False)
        self.ui.pushBtnManual.clicked.connect(self.request_manual)
        self.ui.pushBtnAuto.clicked.connect(self.toggle_auto)

        self.opc.start()

    def on_connection_changed(self, connected, message):
        self.connected = connected
        self.setWindowTitle(f"ESTAMPADOR | {message}")
        self.ui.pushBtnManual.setEnabled(connected)
        self.ui.pushBtnAuto.setEnabled(
            connected
            and self.auto_mode_value is not None
            and self.auto_pending_value is None
        )

    def on_data_received(self, values):
        self.set_spinbox(self.ui.spinBoxMedicion, values.get("measurement_digits"))
        self.set_spinbox(self.ui.spinBoxClase, values.get("measurement_class"))
        self.set_spinbox(self.ui.spinBoxUnidad, values.get("measurement_unit"))
        self.set_spinbox(self.ui.spinBoxLote1, values.get("batch_digits_1"))
        self.set_spinbox(self.ui.spinBoxLote2, values.get("batch_digits_2"))

        self.set_status(
            self.ui.labelMedicionOk, values.get("measurement_ok"), "MEDICIÓN"
        )
        self.set_status(self.ui.labelLoteOk, values.get("batch_ok"), "LOTE")
        self.set_status(self.ui.labelSensoresOK, values.get("sensor_ok"), "SENSORES")

        sensor_status = values.get("sensor_status")
        if sensor_status is not None:
            self.ui.labelConteoSensoresActivos.setText(
                f"Estado sensores: {sensor_status}"
            )

        # autoMode es la solicitud mantenida; autoActive es la confirmación real.
        auto_value = values.get("auto_mode")
        if isinstance(auto_value, bool):
            self.auto_mode_value = auto_value
            if self.auto_pending_value is not None:
                if auto_value == self.auto_pending_value:
                    self.auto_pending_value = None
                    self.auto_pending_cycles = 0
                else:
                    self.auto_pending_cycles += 1
                    if self.auto_pending_cycles >= self.auto_pending_timeout_cycles:
                        print(
                            "[OPC UA] Tiempo de espera agotado al confirmar autoMode. "
                            "Se volverá a habilitar el botón."
                        )
                        self.auto_pending_value = None
                        self.auto_pending_cycles = 0

            self.ui.pushBtnAuto.setEnabled(
                self.connected and self.auto_pending_value is None
            )
        else:
            self.auto_mode_value = None
            self.ui.pushBtnAuto.setEnabled(False)

        # Mostrar exclusivamente los estados reales confirmados por el PLC.
        manual_active = values.get("manual_active")
        auto_active = values.get("auto_active")
        if manual_active is True and auto_active is True:
            mode_text = "ERROR: MANUAL Y AUTOMÁTICO ACTIVOS"
        elif manual_active is True and auto_active is False:
            mode_text = "MANUAL ACTIVO"
        elif auto_active is True and manual_active is False:
            mode_text = "AUTOMÁTICO ACTIVO"
        elif manual_active is False and auto_active is False:
            mode_text = "EN ESPERA DE MODO"
        else:
            mode_text = "SIN CONFIRMACIÓN DEL PLC"

        self.ui.labelStatusMode.setText(mode_text)

    def request_manual(self):
        """Envía un pulso de solicitud; el PLC restablece manualMode a FALSE."""
        if self.connected:
            self.opc.write_value("manual_mode", True)

    def toggle_auto(self):
        """Alterna la solicitud autoMode usando el último valor leído del PLC."""
        if not self.connected or self.auto_mode_value is None:
            return
        if self.auto_pending_value is not None:
            return

        requested_value = not self.auto_mode_value
        self.auto_pending_value = requested_value
        self.auto_pending_cycles = 0
        self.ui.pushBtnAuto.setEnabled(False)
        self.opc.write_value("auto_mode", requested_value)

    @staticmethod
    def set_spinbox(widget, value):
        if value is not None:
            try:
                widget.setValue(int(value))
            except (TypeError, ValueError, OverflowError):
                pass

    @staticmethod
    def set_status(label, value, name):
        if value is None:
            label.setText(f"{name}: SIN DATO")
        else:
            label.setText(f"{name}: {'OK' if bool(value) else 'ERROR'}")

    def on_write_result(self, key, success, message):
        print(f"OPC UA escritura [{key}]: {message}")
        if not success and key == "auto_mode":
            self.auto_pending_value = None
            self.auto_pending_cycles = 0
            self.ui.pushBtnAuto.setEnabled(
                self.connected and self.auto_mode_value is not None
            )

    def closeEvent(self, event):
        self.opc.stop()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Widget()
    window.show()
    sys.exit(app.exec())

import sys
from PySide6.QtWidgets import QApplication, QWidget
from ui_form import Ui_Widget
from opcua_manager import OpcUaWorker

class Widget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_Widget()
        self.ui.setupUi(self)
        self.setWindowTitle("Visualización - PLC B&R")

        self.opc = OpcUaWorker()
        self.opc.connection_changed.connect(self.on_connection_changed)
        self.opc.data_received.connect(self.on_data_received)
        self.opc.write_result.connect(self.on_write_result)
        self.opc.start()

        self.ui.pushBtnManual.clicked.connect(
            lambda: self.opc.write_value("manual_mode", True))
        self.ui.pushBtnAuto.clicked.connect(
            lambda: self.opc.write_value("auto_mode", True))

    def on_connection_changed(self, connected, message):
        self.setWindowTitle("Visualización - PLC B&R | " + message)
        self.ui.labelMedicionOk.setText(
            "OPC UA: CONECTADO" if connected else "OPC UA: DESCONECTADO")

    def on_data_received(self, values):
        self.set_spinbox(self.ui.spinBoxMedicion, values.get("measurement_digits"))
        self.set_spinbox(self.ui.spinBoxClase, values.get("measurement_class"))
        self.set_spinbox(self.ui.spinBoxUnidad, values.get("measurement_unit"))
        self.set_spinbox(self.ui.spinBoxLote1, values.get("batch_digits_1"))
        self.set_spinbox(self.ui.spinBoxLote2, values.get("batch_digits_2"))
        self.set_status(self.ui.labelMedicionOk, values.get("measurement_ok"), "MEDICIÓN")
        self.set_status(self.ui.labelLoteOk, values.get("batch_ok"), "LOTE")
        self.set_status(self.ui.labelSensoresOK, values.get("sensor_ok"), "SENSORES")
        sensor_status = values.get("sensor_status")
        if sensor_status is not None:
            self.ui.labelConteoSensoresActivos.setText(f"Estado sensores: {sensor_status}")

    @staticmethod
    def set_spinbox(widget, value):
        if value is not None:
            try:
                widget.setValue(int(value))
            except (TypeError, ValueError, OverflowError):
                pass

    @staticmethod
    def set_status(label, value, name):
        label.setText(f"{name}: SIN DATO" if value is None else
                      f"{name}: {'OK' if bool(value) else 'ERROR'}")

    def on_write_result(self, key, success, message):
        print(f"OPC UA escritura [{key}]: {message}")

    def closeEvent(self, event):
        self.opc.stop()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Widget()
    window.show()
    sys.exit(app.exec())

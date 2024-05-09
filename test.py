import psutil
import requests
from PyQt5 import QtWidgets, QtCore, QtWebEngineWidgets
import folium
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWidgets import QVBoxLayout, QTextEdit, QLabel
import geoip2.database

class ConexionWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Conexiones de red')
        layout = QVBoxLayout()
        self.label_titulo = QLabel('<h2 style="color: white; text-align: center;">DDLR Active Connections</h2>')
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.map_view = QWebEngineView()  # Widget para mostrar el mapa
        layout.addWidget(self.label_titulo)
        layout.addWidget(self.text_edit)
        layout.addWidget(self.map_view)  # Agregar el widget del mapa al diseño
        self.setLayout(layout)
        self.conexiones_previas = set()
        self.marcadores_previos = []  # Lista para mantener los marcadores anteriores
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.actualizar_info)
        self.timer.start(5000)  # Actualizar cada 5 segundos
        self.actualizar_info()  # Llamar a actualizar_info() para mostrar las conexiones al iniciar

    def obtener_nombre_programa(self, pid):
        try:
            proceso = psutil.Process(pid)
            return proceso.name()
        except psutil.NoSuchProcess:
            return "Unknown"

    def obtener_nombre_proceso_padre(self, pid):
        try:
            proceso = psutil.Process(pid)
            padre = proceso.parent()
            if padre:
                return padre.name()
            return "Unknown"
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return "Unknown"

    def obtener_info_geolocalizacion(self, ip_address):
        reader = geoip2.database.Reader('GeoLite2-City.mmdb')
        try:
            response = reader.city(ip_address)
            latitude = response.location.latitude
            longitude = response.location.longitude
            return latitude, longitude
        except Exception as e:
            print(f"No se pudo obtener la geolocalización para la IP {ip_address}: {e}")
            return None, None

    def obtener_conexiones(self):
        conexiones = {}
        for conn in psutil.net_connections(kind='inet'):
            if conn.raddr:
                tipo = 'Saliente'
                direccion = f"{conn.raddr.ip}:{conn.raddr.port}"
                color = '#1E90FF'  # Color azul para conexiones salientes
            else:
                tipo = 'Entrante'
                direccion = f"{conn.laddr.ip}:{conn.laddr.port}"
                color = '#FF6347'  # Color rojo para conexiones entrantes
            if conn.pid is not None:
                nombre_programa = self.obtener_nombre_programa(conn.pid)
                if nombre_programa == "Unknown":
                    nombre_programa = self.obtener_nombre_proceso_padre(conn.pid)
            else:
                nombre_programa = "Unknown"
            if direccion in conexiones:
                conexiones[direccion]['count'] += 1
            else:
                conexiones[direccion] = {'count': 1, 'tipo': tipo, 'nombre_programa': nombre_programa, 'color': color}
        return conexiones

    def actualizar_info(self):
        conexiones = self.obtener_conexiones()
        texto = ''
        m = folium.Map(location=[0, 0], zoom_start=0.5, tiles='CartoDB.DarkMatter')  # Crear el mapa con Folium

        # Limpiar los marcadores anteriores
        for marcador in self.marcadores_previos:
            m.add_child(marcador)  # Agregar el marcador al mapa

        self.marcadores_previos = []  # Vaciar la lista de marcadores previos

        for direccion, info in conexiones.items():
            if info['count'] > 1:
                texto += f"<span style='color: {info['color']}; font-size: 12px;'>{info['nombre_programa']} - Tipo: {info['tipo']} - Dirección: {direccion} ({info['count']} conexiones)</span><br>"
            else:
                texto += f"<span style='color: {info['color']}; font-size: 12px;'>{info['nombre_programa']} - Tipo: {info['tipo']} - Dirección: {direccion}</span><br>"
            
            # Obtener la IP de la dirección
            ip_address = direccion.split(':')[0]

            # Obtener la información de geolocalización
            latitude, longitude = self.obtener_info_geolocalizacion(ip_address)

            # Agregar un punto al mapa con el color correspondiente
            if latitude is not None and longitude is not None:
                tooltip = f"{info['nombre_programa']} - {info['tipo']} - {direccion}"
                folium.CircleMarker([latitude, longitude], radius=5, color=info['color'], tooltip=tooltip).add_to(m)

        # Guardar el mapa como un archivo HTML
        m.save('map.html')

        # Cargar el mapa en el widget QWebEngineView
        self.map_view.load(QtCore.QUrl.fromLocalFile(QtCore.QFileInfo('map.html').absoluteFilePath()))

        # Actualizar el texto en el QTextEdit
        self.text_edit.setHtml(texto)

if __name__ == '__main__':
    app = QtWidgets.QApplication([])

    # Crear el widget
    widget = ConexionWidget()
    widget.resize(800, 600)

    # Obtener la geometría de la pantalla y las coordenadas de la esquina superior derecha
    screen_geometry = QtWidgets.QDesktopWidget().availableGeometry()
    x = screen_geometry.topRight().x() - widget.width()
    y = screen_geometry.topRight().y()

    # Mover el widget a la esquina superior derecha de la pantalla
    widget.move(x, y)

    # Quitar la barra de título
    widget.setWindowFlags(QtCore.Qt.FramelessWindowHint)

    # Establecer opacidad del widget (70%)
    widget.setWindowOpacity(0.7)

    widget.show()
    app.exec_()

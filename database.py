import sqlite3
from werkzeug.security import generate_password_hash

DB_NAME = "inventario_pyme.db"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    # Inicializa la estructura de base datos y datos semilla
    conn = get_db_connection()
    c = conn.cursor()
    
    # Tabla Usuarios
    c.execute('''CREATE TABLE IF NOT EXISTS usuarios 
                 (id INTEGER PRIMARY KEY, username TEXT, password TEXT, rol TEXT)''')
    
    # Tabla Productos
    c.execute('''CREATE TABLE IF NOT EXISTS productos 
                 (id INTEGER PRIMARY KEY, sku TEXT UNIQUE, nombre TEXT, precio REAL, 
                  stock INTEGER, minimo INTEGER, categoria TEXT)''')
    
    # Tabla Movimientos
    c.execute('''CREATE TABLE IF NOT EXISTS movimientos 
                 (id INTEGER PRIMARY KEY, producto_sku TEXT, tipo TEXT, cantidad INTEGER, 
                  fecha TEXT, usuario TEXT)''')
    
    # Crear admin por defecto si no existe
    c.execute("SELECT * FROM usuarios WHERE username='admin'")
    if not c.fetchone():
        print("Creando datos de prueba con contraseñas encriptadas...")
        
        # --- ENCRIPTACIÓN ---
        pass_admin = generate_password_hash('1234')
        pass_bodega = generate_password_hash('1234')
        
        c.execute("INSERT INTO usuarios (username, password, rol) VALUES (?, ?, ?)", 
                  ('admin', pass_admin, 'admin'))
        c.execute("INSERT INTO usuarios (username, password, rol) VALUES (?, ?, ?)", 
                  ('bodega', pass_bodega, 'bodeguero'))
        
        # Productos de prueba
        c.execute("INSERT INTO productos (sku, nombre, precio, stock, minimo, categoria) VALUES ('111', 'Martillo Pro', 5000, 15, 5, 'Herramientas')")
        c.execute("INSERT INTO productos (sku, nombre, precio, stock, minimo, categoria) VALUES ('222', 'Taladro 500W', 35000, 2, 5, 'Maquinaria')")
    
    conn.commit()
    conn.close()
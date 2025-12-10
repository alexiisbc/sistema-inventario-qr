from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from database import init_db, get_db_connection
from werkzeug.security import check_password_hash
from datetime import datetime
import os

# Configuración de la app
app = Flask(__name__)
app.secret_key = "clave_secreta_proyecto_titulo"

# Inicializar Base de Datos
if not os.path.exists("inventario_pyme.db"):
    init_db()

# --- RUTAS DE VISTAS ---

@app.route('/')
def index():
    if 'usuario' not in session:
        return redirect(url_for('login_view'))
    
    conn = get_db_connection()
    productos = conn.execute('SELECT * FROM productos ORDER BY stock ASC').fetchall()
    conn.close()
    
    total_prods = sum([p['stock'] for p in productos])
    criticos = sum([1 for p in productos if p['stock'] <= p['minimo']])
    valor_total = sum([p['stock'] * p['precio'] for p in productos])
    
    stats = {
        'total_productos': total_prods, 
        'criticos': criticos, 
        'valor_total': "{:,.0f}".format(valor_total).replace(',', '.')
    }
    return render_template('dashboard.html', productos=productos, stats=stats)

@app.route('/login', methods=['GET', 'POST'])
def login_view():
    if request.method == 'GET':
        if 'usuario' in session:
            return redirect(url_for('index'))
        return render_template('login.html')
        
    username = request.form['username']
    password = request.form['password']
    
    conn = get_db_connection()

    # 1. Buscamos SOLO por nombre de usuario
    user = conn.execute('SELECT * FROM usuarios WHERE username = ?', (username,)).fetchone()
    conn.close()
    
    # 2. Verificamos la contraseña usando la librería de seguridad
    if user and check_password_hash(user['password'], password):
        session['usuario'] = user['username']
        session['rol'] = user['rol']
        flash(f'¡Bienvenido, {user["username"]}!', 'success')
        return redirect(url_for('index'))
    else:
        flash('Credenciales incorrectas.', 'danger')
        return redirect(url_for('login_view'))

@app.route('/logout')
def logout():
    session.clear()
    flash('Has cerrado sesión correctamente.', 'info')
    return redirect(url_for('login_view'))

@app.route('/add_product', methods=['POST'])
def add_product():
    if session.get('rol') != 'admin': return redirect(url_for('index'))
    try:
        conn = get_db_connection()
        conn.execute('INSERT INTO productos (sku, nombre, precio, stock, minimo, categoria) VALUES (?, ?, ?, ?, ?, ?)',
                     (request.form['sku'], request.form['nombre'], request.form['precio'], 
                      request.form['stock'], request.form['minimo'], request.form['categoria']))
        conn.commit()
        conn.close()
        flash('Producto agregado.', 'success')
    except:
        flash('Error al agregar.', 'danger')
    return redirect(url_for('index'))

@app.route('/delete_product/<int:id>')
def delete_product(id):
    if session.get('rol') != 'admin': return redirect(url_for('index'))
    conn = get_db_connection()
    conn.execute('DELETE FROM productos WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('Producto eliminado.', 'info')
    return redirect(url_for('index'))

# --- RUTA PARA MOVIMIENTOS MANUAL ---
@app.route('/movement', methods=['POST'])
def movement():
    if 'usuario' not in session: return redirect(url_for('login_view'))
    return procesar_movimiento(request.form['sku'], request.form['tipo'], int(request.form['cantidad']), es_api=False)

# --- API PARA MODO CONTINUO (JSON) ---
@app.route('/api/movement', methods=['POST'])
def api_movement():
    if 'usuario' not in session: return jsonify({'status': 'error', 'msg': 'Sesión expirada'}), 401
    data = request.json
    return procesar_movimiento(data['sku'], data['tipo'], 1, es_api=True)

# --- LÓGICA COMPARTIDA ---
def procesar_movimiento(sku, tipo, cantidad, es_api=False):
    conn = get_db_connection()
    prod = conn.execute('SELECT * FROM productos WHERE sku = ?', (sku,)).fetchone()
    
    if not prod:
        conn.close()
        msg = f'Producto no encontrado (SKU: {sku})'
        if es_api: return jsonify({'status': 'error', 'msg': msg})
        flash(msg, 'danger')
        return redirect(url_for('index'))
    
    nuevo_stock = prod['stock']
    if tipo == 'entrada':
        nuevo_stock += cantidad
    elif tipo == 'salida':
        if prod['stock'] >= cantidad:
            nuevo_stock -= cantidad
        else:
            conn.close()
            msg = f'Stock insuficiente ({prod["stock"]})'
            if es_api: return jsonify({'status': 'error', 'msg': msg})
            flash(msg, 'danger')
            return redirect(url_for('index'))
            
    conn.execute('UPDATE productos SET stock = ? WHERE id = ?', (nuevo_stock, prod['id']))
    conn.execute('INSERT INTO movimientos (producto_sku, tipo, cantidad, fecha, usuario) VALUES (?, ?, ?, ?, ?)',
                 (sku, tipo, cantidad, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), session['usuario']))
    conn.commit()
    conn.close()
    
    msg = f'{prod["nombre"]} | Nuevo Stock: {nuevo_stock}'
    
    if es_api:
        # Respuesta rápida para el modo continuo
        return jsonify({'status': 'success', 'msg': msg, 'sku': sku, 'stock': nuevo_stock, 'nombre': prod['nombre']})
    else:
        flash(f'Movimiento registrado: {msg}', 'success')
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
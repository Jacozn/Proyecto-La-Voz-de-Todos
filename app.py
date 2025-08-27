from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from flask_bcrypt import Bcrypt
from itsdangerous import URLSafeTimedSerializer
import sendgrid 
from sendgrid.helpers.mail import Mail, Email, To, Content
import sqlite3
import os
from werkzeug.utils import secure_filename
from datetime import datetime
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

app = Flask(__name__)
app.secret_key = 'advpjsh'

# Configuraciones
SENDGRID_API_KEY = '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'

# Serializador para crear y verificar tokens
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])

# Configuración
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Crear carpeta de uploads si no existe
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with open('scripts/create_database.sql', 'r') as f:
        sql_script = f.read()
    
    conn = get_db_connection()
    conn.executescript(sql_script)
    conn.close()

# Decorador para verificar autenticación
def login_required(f):
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# Decorador para verificar rol de admin
def admin_required(f):
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('rol') != 'admin':
            flash('Acceso denegado. Se requieren permisos de administrador.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM usuarios WHERE email = ? AND password = ?', 
                           (email, password)).fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user['id']
            session['nombre'] = user['nombre']
            session['rol'] = user['rol']
            flash('Inicio de sesión exitoso', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Email o contraseña incorrectos', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nombre = request.form['nombre']
        email = request.form['email']
        password = request.form['password']
        
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO usuarios (nombre, email, password) VALUES (?, ?, ?)',
                        (nombre, email, password))
            conn.commit()
            flash('Registro exitoso. Puedes iniciar sesión ahora.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('El email ya está registrado', 'error')
        finally:
            conn.close()
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada exitosamente', 'success')
    return redirect(url_for('login'))

@app.route('/crear_usuario_admin', methods=['GET', 'POST'])
@admin_required
def crear_usuario_admin():
    if request.method == 'POST':
        nombre = request.form['nombre']
        email = request.form['email']
        password = request.form['password']
        rol = request.form['rol']
        
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO usuarios (nombre, email, password, rol) VALUES (?, ?, ?, ?)',
                        (nombre, email, password, rol))
            conn.commit()
            flash('Usuario creado exitosamente', 'success')
            return redirect(url_for('dashboard'))
        except sqlite3.IntegrityError:
            flash('El email ya está registrado', 'error')
        finally:
            conn.close()
    
    return render_template('crear_usuario_admin.html')

#Dashboard de Olvide mi contraseña--------------------------------------------------------------------------------------------------------
@app.route('/recuperar_contrasena_correo', methods=['GET', 'POST'])
def recuperar_contrasena_correo():
    if request.method == 'POST':
        correo = request.form['email']
        
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM usuarios WHERE email = ?", (correo,))
        usuario = cursor.fetchone()
        conn.close()

        if usuario:
            token = serializer.dumps(correo, salt='recuperar-contrasena')
            enlace = url_for('nueva_contrasena', token=token, _external=True)
            mensaje_html = f"""
            Hola, hemos recibido una solicitud para restablecer tu contraseña.<br><br>
            Si no has solicitado este cambio, ignora este mensaje.<br><br>
            Para restablecer tu contraseña, haz clic en el siguiente enlace:<br><br>
            <a href="{enlace}">Restablecer contraseña</a>
            """

            # Construcción del email con SendGrid
            sg = sendgrid.SendGridAPIClient(api_key=SENDGRID_API_KEY)
            from_email = Email("h69442305@gmail.com", name="Sistema de Junta Vecinal")
            to_email = To(correo)
            subject = "Recuperación de contraseña"
            content = Content("text/html", mensaje_html)
            mail = Mail(from_email, to_email, subject, content)

            try:
                response = sg.send(mail)
                if response.status_code in [200, 202]:
                    flash('Se ha enviado un enlace de recuperación a tu correo.', 'success')
                    return redirect(url_for('login'))
                else:
                    flash('Error al enviar el correo. Inténtalo más tarde.', 'danger')
            except Exception as e:
                flash('Error al conectar con el servicio de correo.', 'danger')
                print(e)
        else:
            flash('Correo no registrado en el sistema.', 'warning')

    return render_template('recuperar_contrasena_correo.html')

@app.route('/nueva_contrasena/<token>', methods=['GET', 'POST'])
def nueva_contrasena(token):
    try:
        correo = serializer.loads(token, salt='recuperar-contrasena', max_age=3600)
    except Exception:
        flash('El enlace ha expirado o no es válido.', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        nueva = request.form['nueva_contrasena']
        confirmar = request.form['confirmar_contrasena']
        
        if nueva != confirmar:
            flash('Las contraseñas no coinciden.', 'warning')
        else:
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE usuarios
                SET password = ?
                WHERE email = ?
            """, (nueva, correo))
            conn.commit()
            conn.close()

            flash('Tu contraseña ha sido actualizada correctamente.', 'success')
            return redirect(url_for('login'))

    return render_template('nueva_contrasena.html')

#-----------------------------------------------------------------------------------------------------------------------------------------

@app.route('/dashboard')
@login_required
def dashboard():
    if session['rol'] == 'admin':
        return render_template('dashboard_admin.html')
    else:
        return render_template('dashboard_vecino.html')

# RUTAS DE DENUNCIAS
@app.route('/denuncias')
@login_required
def denuncias():
    # Obtener los filtros del formulario GET
    busqueda = request.args.get('busqueda', '').strip()
    categoria = request.args.get('categoria', '').strip()
    estado = request.args.get('estado', '').strip()
    fecha_inicio = request.args.get('fecha_inicio', '').strip()
    fecha_fin = request.args.get('fecha_fin', '').strip()
    
    conn = get_db_connection()
    
    if session['rol'] == 'admin':
        query = '''
            SELECT d.*, u.nombre as usuario_nombre 
            FROM denuncias d 
            JOIN usuarios u ON d.usuario_id = u.id 
            WHERE 1=1
        '''
        params = []
        
        if busqueda:
            query += ' AND (d.titulo LIKE ? OR d.categoria LIKE ? OR u.nombre LIKE ?)'
            params.extend([f'%{busqueda}%', f'%{busqueda}%', f'%{busqueda}%'])
        
        if categoria:
            query += ' AND d.categoria = ?'
            params.append(categoria)
        
        if estado:
            query += ' AND d.estado = ?'
            params.append(estado)
        
        if fecha_inicio:
            query += ' AND DATE(d.fecha_creacion) >= ?'
            params.append(fecha_inicio)
        
        if fecha_fin:
            query += ' AND DATE(d.fecha_creacion) <= ?'
            params.append(fecha_fin)
        
        query += ' ORDER BY d.fecha_creacion DESC'
        denuncias = conn.execute(query, params).fetchall()
    else:
        query = '''
            SELECT * FROM denuncias 
            WHERE usuario_id = ?
        '''
        params = [session['user_id']]
        
        if busqueda:
            query += ' AND (titulo LIKE ? OR categoria LIKE ?)'
            params.extend([f'%{busqueda}%', f'%{busqueda}%'])
        
        if categoria:
            query += ' AND categoria = ?'
            params.append(categoria)
        
        if estado:
            query += ' AND estado = ?'
            params.append(estado)
        
        if fecha_inicio:
            query += ' AND DATE(fecha_creacion) >= ?'
            params.append(fecha_inicio)
        
        if fecha_fin:
            query += ' AND DATE(fecha_creacion) <= ?'
            params.append(fecha_fin)
        
        query += ' ORDER BY fecha_creacion DESC'
        denuncias = conn.execute(query, params).fetchall()
    
    conn.close()
    
    return render_template('denuncias.html', denuncias=denuncias)

@app.route('/nueva_denuncia', methods=['GET', 'POST'])
@login_required
def nueva_denuncia():
    if request.method == 'POST':
        titulo = request.form['titulo']
        descripcion = request.form['descripcion']
        categoria = request.form['categoria']
        
        imagen_path = None
        if 'imagen' in request.files:
            file = request.files['imagen']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
                filename = timestamp + filename
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                imagen_path = filename
        
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO denuncias (usuario_id, titulo, descripcion, categoria, imagen_path)
            VALUES (?, ?, ?, ?, ?)
        ''', (session['user_id'], titulo, descripcion, categoria, imagen_path))
        conn.commit()
        conn.close()
        
        flash('Denuncia creada exitosamente', 'success')
        return redirect(url_for('denuncias'))
    
    return render_template('nueva_denuncia.html')

@app.route('/responder_denuncia/<int:denuncia_id>', methods=['POST'])
@admin_required
def responder_denuncia(denuncia_id):
    respuesta = request.form['respuesta']
    estado = request.form['estado']
    
    conn = get_db_connection()
    conn.execute('''
        UPDATE denuncias 
        SET respuesta_admin = ?, estado = ?, fecha_actualizacion = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (respuesta, estado, denuncia_id))
    conn.commit()
    conn.close()
    
    flash('Respuesta enviada exitosamente', 'success')
    return redirect(url_for('denuncias'))

@app.route('/eliminar_denuncia/<int:denuncia_id>')
@admin_required
def eliminar_denuncia(denuncia_id):
    conn = get_db_connection()
    
    # Verificar que la denuncia existe y está resuelta
    denuncia = conn.execute('SELECT * FROM denuncias WHERE id = ? AND estado = "resuelto"', (denuncia_id,)).fetchone()
    
    if not denuncia:
        flash('Solo se pueden eliminar denuncias con estado "Resuelto"', 'error')
        conn.close()
        return redirect(url_for('denuncias'))
    
    # Eliminar la denuncia
    conn.execute('DELETE FROM denuncias WHERE id = ?', (denuncia_id,))
    conn.commit()
    conn.close()
    
    flash('Denuncia eliminada exitosamente', 'success')
    return redirect(url_for('denuncias'))

@app.route('/descargar_denuncia_pdf/<int:denuncia_id>')
@login_required
def descargar_denuncia_pdf(denuncia_id):
    conn = get_db_connection()
    denuncia = conn.execute('''
        SELECT d.*, u.nombre as usuario_nombre 
        FROM denuncias d 
        JOIN usuarios u ON d.usuario_id = u.id 
        WHERE d.id = ?
    ''', (denuncia_id,)).fetchone()
    conn.close()
    
    if not denuncia or (session['rol'] != 'admin' and denuncia['usuario_id'] != session['user_id']):
        flash('Denuncia no encontrada o sin permisos', 'error')
        return redirect(url_for('denuncias'))
    
    # Crear PDF
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    
    # Contenido del PDF
    p.drawString(100, 750, f"DENUNCIA #{denuncia['id']}")
    p.drawString(100, 720, f"Título: {denuncia['titulo']}")
    p.drawString(100, 690, f"Usuario: {denuncia['usuario_nombre']}")
    p.drawString(100, 660, f"Categoría: {denuncia['categoria']}")
    p.drawString(100, 630, f"Estado: {denuncia['estado']}")
    p.drawString(100, 600, f"Fecha: {denuncia['fecha_creacion']}")
    
    # Descripción (con salto de línea)
    p.drawString(100, 570, "Descripción:")
    descripcion_lines = denuncia['descripcion'].split('\n')
    y_pos = 550
    for line in descripcion_lines:
        p.drawString(120, y_pos, line[:80])  # Limitar caracteres por línea
        y_pos -= 20
    
    if denuncia['respuesta_admin']:
        p.drawString(100, y_pos - 20, "Respuesta del Administrador:")
        respuesta_lines = denuncia['respuesta_admin'].split('\n')
        y_pos -= 40
        for line in respuesta_lines:
            p.drawString(120, y_pos, line[:80])
            y_pos -= 20
    
    p.save()
    buffer.seek(0)
    
    return send_file(buffer, as_attachment=True, download_name=f'denuncia_{denuncia_id}.pdf', mimetype='application/pdf')

@app.route('/ver_denuncia/<int:denuncia_id>')
@login_required
def ver_denuncia(denuncia_id):
    conn = get_db_connection()
    denuncia = conn.execute('''
        SELECT d.*, u.nombre as usuario_nombre 
        FROM denuncias d 
        JOIN usuarios u ON d.usuario_id = u.id 
        WHERE d.id = ?
    ''', (denuncia_id,)).fetchone()
    conn.close()
    
    if not denuncia or (session['rol'] != 'admin' and denuncia['usuario_id'] != session['user_id']):
        flash('Denuncia no encontrada o sin permisos', 'error')
        return redirect(url_for('denuncias'))
    
    # Convertir Row a dict para JSON
    denuncia_dict = dict(denuncia)
    return jsonify(denuncia_dict)

# RUTAS DE NOTICIAS
@app.route('/noticias')
@login_required
def noticias():
    # Obtener los filtros del formulario GET
    busqueda = request.args.get('busqueda', '').strip()
    fecha_inicio = request.args.get('fecha_inicio', '').strip()
    fecha_fin = request.args.get('fecha_fin', '').strip()
    conn = get_db_connection()
    
    query = 'SELECT * FROM noticias WHERE activa = 1'
    params = []

    if busqueda:
        query += ' AND titulo LIKE ?'
        params.append(f'%{busqueda}%')

    if fecha_inicio:
        query += ' AND DATE(fecha_publicacion) >= ?'
        params.append(fecha_inicio)

    if fecha_fin:
        query += ' AND DATE(fecha_publicacion) <= ?'
        params.append(fecha_fin)

    query += ' ORDER BY fecha_publicacion DESC'
    noticias = conn.execute(query, params).fetchall()
    conn.close()

    # Convertimos a diccionarios para que sean serializables con tojson
    noticias_list = [dict(noticia) for noticia in noticias]
    return render_template('noticias.html', noticias=noticias_list)

@app.route('/nueva_noticia', methods=['GET', 'POST'])
@admin_required
def nueva_noticia():
    if request.method == 'POST':
        titulo = request.form['titulo']
        descripcion = request.form['descripcion']
        
        imagen_path = None
        if 'imagen' in request.files:
            file = request.files['imagen']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
                filename = timestamp + filename
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                imagen_path = filename
        
        conn = get_db_connection()
        conn.execute('INSERT INTO noticias (titulo, descripcion, imagen_path) VALUES (?, ?, ?)',
                    (titulo, descripcion, imagen_path))
        conn.commit()
        conn.close()
        
        flash('Noticia creada exitosamente', 'success')
        return redirect(url_for('noticias'))
    
    return render_template('nueva_noticia.html')

@app.route('/editar_noticia/<int:noticia_id>', methods=['GET', 'POST'])
@admin_required
def editar_noticia(noticia_id):
    conn = get_db_connection()
    
    if request.method == 'POST':
        titulo = request.form['titulo']
        descripcion = request.form['descripcion']
        
        # Manejar imagen
        imagen_path = request.form.get('imagen_actual')
        if 'imagen' in request.files:
            file = request.files['imagen']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
                filename = timestamp + filename
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                imagen_path = filename
        
        conn.execute('UPDATE noticias SET titulo = ?, descripcion = ?, imagen_path = ? WHERE id = ?',
                    (titulo, descripcion, imagen_path, noticia_id))
        conn.commit()
        conn.close()
        
        flash('Noticia actualizada exitosamente', 'success')
        return redirect(url_for('noticias'))
    
    noticia = conn.execute('SELECT * FROM noticias WHERE id = ?', (noticia_id,)).fetchone()
    conn.close()
    
    return render_template('editar_noticia.html', noticia=noticia)

@app.route('/eliminar_noticia/<int:noticia_id>')
@admin_required
def eliminar_noticia(noticia_id):
    conn = get_db_connection()
    conn.execute('UPDATE noticias SET activa = 0 WHERE id = ?', (noticia_id,))
    conn.commit()
    conn.close()
    
    flash('Noticia eliminada exitosamente', 'success')
    return redirect(url_for('noticias'))

# RUTAS DE EVENTOS
@app.route('/eventos')
@login_required
def eventos():
    busqueda = request.args.get('busqueda', '').strip()
    fecha_inicio = request.args.get('fecha_inicio', '')
    fecha_fin = request.args.get('fecha_fin', '')
    conn = get_db_connection()
    cursor = conn.cursor()

    # Filtros dinámicos para eventos generales
    filtros = ["e.activo = 1"]
    params = []

    if busqueda:
        filtros.append("e.titulo LIKE ?")
        params.append(f"%{busqueda}%")

    if fecha_inicio:
        filtros.append("e.fecha_evento >= ?")
        params.append(fecha_inicio)

    if fecha_fin:
        filtros.append("e.fecha_evento <= ?")
        params.append(fecha_fin)

    where_clause = " AND ".join(filtros)

    # Consulta principal de eventos con conteo de inscripciones
    query = f'''
        SELECT e.*, COUNT(i.usuario_id) AS inscripciones_actuales
        FROM eventos e
        LEFT JOIN inscripciones_eventos i ON e.id = i.evento_id
        WHERE {where_clause}
        GROUP BY e.id
        ORDER BY e.fecha_evento ASC
    '''
    eventos = cursor.execute(query, params).fetchall()

    # Variables para el vecino
    inscripciones = []
    eventos_inscritos = []

    if session['rol'] == 'vecino':
        user_id = session['user_id']

        # Obtener IDs de inscripciones
        inscripciones_query = '''
            SELECT evento_id FROM inscripciones_eventos WHERE usuario_id = ?
        '''
        inscripciones_raw = cursor.execute(inscripciones_query, (user_id,)).fetchall()
        inscripciones = [i['evento_id'] for i in inscripciones_raw]

        # Filtros también para eventos inscritos
        filtros_inscritos = [
            "i.usuario_id = ?",
            "e.activo = 1"
        ]
        params_inscritos = [user_id]

        if busqueda:
            filtros_inscritos.append("e.titulo LIKE ?")
            params_inscritos.append(f"%{busqueda}%")

        if fecha_inicio:
            filtros_inscritos.append("e.fecha_evento >= ?")
            params_inscritos.append(fecha_inicio)

        if fecha_fin:
            filtros_inscritos.append("e.fecha_evento <= ?")
            params_inscritos.append(fecha_fin)

        where_clause_inscritos = " AND ".join(filtros_inscritos)

        eventos_inscritos_query = f'''
            SELECT e.*, COUNT(i2.usuario_id) AS inscripciones_actuales
            FROM eventos e
            JOIN inscripciones_eventos i ON e.id = i.evento_id
            LEFT JOIN inscripciones_eventos i2 ON e.id = i2.evento_id
            WHERE {where_clause_inscritos}
            GROUP BY e.id
            ORDER BY e.fecha_evento ASC
        '''
        eventos_inscritos_data = cursor.execute(eventos_inscritos_query, params_inscritos).fetchall()
        eventos_inscritos = [dict(evento) for evento in eventos_inscritos_data]

    conn.close()
    eventos_list = [dict(evento) for evento in eventos]

    return render_template(
        'eventos.html',
        eventos=eventos_list,
        inscripciones=inscripciones,
        eventos_inscritos=eventos_inscritos
    )

@app.route('/nuevo_evento', methods=['GET', 'POST'])
@admin_required
def nuevo_evento():
    if request.method == 'POST':
        titulo = request.form['titulo']
        descripcion = request.form['descripcion']
        fecha_evento = request.form['fecha_evento']
        lugar = request.form['lugar']
        cupo_maximo = request.form['cupo_maximo']
        
        imagen_path = None
        if 'imagen' in request.files:
            file = request.files['imagen']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
                filename = timestamp + filename
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                imagen_path = filename
        
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO eventos (titulo, descripcion, fecha_evento, lugar, cupo_maximo, imagen_path)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (titulo, descripcion, fecha_evento, lugar, cupo_maximo, imagen_path))
        conn.commit()
        conn.close()
        
        flash('Evento creado exitosamente', 'success')
        return redirect(url_for('eventos'))
    
    return render_template('nuevo_evento.html')

@app.route('/editar_evento/<int:evento_id>', methods=['GET', 'POST'])
@admin_required
def editar_evento(evento_id):
    conn = get_db_connection()
    
    if request.method == 'POST':
        titulo = request.form['titulo']
        descripcion = request.form['descripcion']
        fecha_evento = request.form['fecha_evento']
        lugar = request.form['lugar']
        cupo_maximo = request.form['cupo_maximo']
        
        # Manejar imagen
        imagen_path = request.form.get('imagen_actual')
        if 'imagen' in request.files:
            file = request.files['imagen']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
                filename = timestamp + filename
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                imagen_path = filename
        
        conn.execute('''
            UPDATE eventos 
            SET titulo = ?, descripcion = ?, fecha_evento = ?, lugar = ?, cupo_maximo = ?, imagen_path = ?
            WHERE id = ?
        ''', (titulo, descripcion, fecha_evento, lugar, cupo_maximo, imagen_path, evento_id))
        conn.commit()
        conn.close()
        
        flash('Evento actualizado exitosamente', 'success')
        return redirect(url_for('eventos'))
    
    evento = conn.execute('SELECT * FROM eventos WHERE id = ?', (evento_id,)).fetchone()
    conn.close()
    
    if not evento:
        flash('Evento no encontrado', 'error')
        return redirect(url_for('eventos'))
    
    return render_template('editar_evento.html', evento=evento)

@app.route('/eliminar_evento/<int:evento_id>')
@admin_required
def eliminar_evento(evento_id):
    conn = get_db_connection()
    
    # Verificar que el evento existe
    evento = conn.execute('SELECT * FROM eventos WHERE id = ?', (evento_id,)).fetchone()
    
    if not evento:
        flash('Evento no encontrado', 'error')
        conn.close()
        return redirect(url_for('eventos'))
    
    # Eliminar inscripciones del evento
    conn.execute('DELETE FROM inscripciones_eventos WHERE evento_id = ?', (evento_id,))
    
    # Marcar evento como inactivo (soft delete)
    conn.execute('UPDATE eventos SET activo = 0 WHERE id = ?', (evento_id,))
    conn.commit()
    conn.close()
    
    flash('Evento eliminado exitosamente', 'success')
    return redirect(url_for('eventos'))

@app.route('/inscribirse_evento/<int:evento_id>')
@login_required
def inscribirse_evento(evento_id):
    if session['rol'] != 'vecino':
        flash('Solo los vecinos pueden inscribirse a eventos', 'error')
        return redirect(url_for('eventos'))
    
    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO inscripciones_eventos (usuario_id, evento_id) VALUES (?, ?)',
                    (session['user_id'], evento_id))
        conn.commit()
        flash('Inscripción exitosa', 'success')
    except sqlite3.IntegrityError:
        flash('Ya estás inscrito en este evento', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('eventos'))

@app.route('/desinscribirse_evento/<int:evento_id>')
@login_required
def desinscribirse_evento(evento_id):
    if session['rol'] != 'vecino':
        flash('Solo los vecinos pueden desinscribirse de eventos', 'error')
        return redirect(url_for('eventos'))
    
    conn = get_db_connection()
    result = conn.execute('DELETE FROM inscripciones_eventos WHERE usuario_id = ? AND evento_id = ?',
                         (session['user_id'], evento_id))
    
    if result.rowcount > 0:
        conn.commit()
        flash('Te has desinscrito del evento exitosamente', 'success')
    else:
        flash('No estabas inscrito en este evento', 'error')
    
    conn.close()
    return redirect(url_for('eventos'))

@app.route('/mis_eventos')
@login_required
def mis_eventos():
    if session['rol'] != 'vecino':
        flash('Solo los vecinos pueden ver sus eventos inscritos', 'error')
        return redirect(url_for('dashboard'))
    
    conn = get_db_connection()
    eventos_inscritos = conn.execute('''
        SELECT e.*, 
               COUNT(i2.usuario_id) as inscripciones_actuales
        FROM eventos e
        JOIN inscripciones_eventos i ON e.id = i.evento_id
        LEFT JOIN inscripciones_eventos i2 ON e.id = i2.evento_id
        WHERE i.usuario_id = ? AND e.activo = 1
        GROUP BY e.id
        ORDER BY e.fecha_evento ASC
    ''', (session['user_id'],)).fetchall()
    conn.close()
    
    # Convertir Row objects a diccionarios
    eventos_list = [dict(evento) for evento in eventos_inscritos]
    
    return render_template('mis_eventos.html', eventos_inscritos=eventos_list)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename))

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)

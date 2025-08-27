import sqlite3
from datetime import datetime

def conectar_bd():
    """Conectar a la base de datos"""
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row  # Para acceder por nombre de columna
    return conn

def ver_todos_usuarios():
    """Ver todos los usuarios registrados"""
    conn = conectar_bd()
    usuarios = conn.execute('SELECT * FROM usuarios ORDER BY fecha_registro DESC').fetchall()
    conn.close()
    
    print("=" * 80)
    print("👥 TODOS LOS USUARIOS REGISTRADOS")
    print("=" * 80)
    
    for usuario in usuarios:
        print(f"ID: {usuario['id']}")
        print(f"Nombre: {usuario['nombre']}")
        print(f"Email: {usuario['email']}")
        print(f"Rol: {usuario['rol']}")
        print(f"Fecha registro: {usuario['fecha_registro']}")
        print(f"Activo: {'Sí' if usuario['activo'] else 'No'}")
        print("-" * 50)

def ver_estadisticas_denuncias():
    """Ver estadísticas de denuncias"""
    conn = conectar_bd()
    
    # Total de denuncias
    total = conn.execute('SELECT COUNT(*) as total FROM denuncias').fetchone()
    
    # Por estado
    estados = conn.execute('''
        SELECT estado, COUNT(*) as cantidad 
        FROM denuncias 
        GROUP BY estado
    ''').fetchall()
    
    # Por categoría
    categorias = conn.execute('''
        SELECT categoria, COUNT(*) as cantidad 
        FROM denuncias 
        GROUP BY categoria
    ''').fetchall()
    
    conn.close()
    
    print("=" * 80)
    print("📊 ESTADÍSTICAS DE DENUNCIAS")
    print("=" * 80)
    print(f"Total de denuncias: {total['total']}")
    print("\nPor estado:")
    for estado in estados:
        print(f"  - {estado['estado']}: {estado['cantidad']}")
    
    print("\nPor categoría:")
    for categoria in categorias:
        print(f"  - {categoria['categoria']}: {categoria['cantidad']}")

def ver_denuncias_detalladas():
    """Ver todas las denuncias con detalles"""
    conn = conectar_bd()
    denuncias = conn.execute('''
        SELECT d.*, u.nombre as usuario_nombre, u.email as usuario_email
        FROM denuncias d
        JOIN usuarios u ON d.usuario_id = u.id
        ORDER BY d.fecha_creacion DESC
    ''').fetchall()
    conn.close()
    
    print("=" * 80)
    print("📩 TODAS LAS DENUNCIAS")
    print("=" * 80)
    
    for denuncia in denuncias:
        print(f"ID: {denuncia['id']}")
        print(f"Título: {denuncia['titulo']}")
        print(f"Usuario: {denuncia['usuario_nombre']} ({denuncia['usuario_email']})")
        print(f"Categoría: {denuncia['categoria']}")
        print(f"Estado: {denuncia['estado']}")
        print(f"Fecha: {denuncia['fecha_creacion']}")
        print(f"Descripción: {denuncia['descripcion'][:100]}...")
        if denuncia['imagen_path']:
            print(f"Imagen: {denuncia['imagen_path']}")
        if denuncia['respuesta_admin']:
            print(f"Respuesta admin: {denuncia['respuesta_admin'][:100]}...")
        print("-" * 50)

def ver_noticias():
    """Ver todas las noticias"""
    conn = conectar_bd()
    noticias = conn.execute('SELECT * FROM noticias ORDER BY fecha_publicacion DESC').fetchall()
    conn.close()
    
    print("=" * 80)
    print("📰 TODAS LAS NOTICIAS")
    print("=" * 80)
    
    for noticia in noticias:
        print(f"ID: {noticia['id']}")
        print(f"Título: {noticia['titulo']}")
        print(f"Fecha: {noticia['fecha_publicacion']}")
        print(f"Activa: {'Sí' if noticia['activa'] else 'No'}")
        print(f"Descripción: {noticia['descripcion'][:100]}...")
        if noticia['imagen_path']:
            print(f"Imagen: {noticia['imagen_path']}")
        print("-" * 50)

def ver_eventos():
    """Ver todos los eventos"""
    conn = conectar_bd()
    eventos = conn.execute('SELECT * FROM eventos ORDER BY fecha_evento DESC').fetchall()
    conn.close()
    
    print("=" * 80)
    print("📅 TODOS LOS EVENTOS")
    print("=" * 80)
    
    for evento in eventos:
        print(f"ID: {evento['id']}")
        print(f"Título: {evento['titulo']}")
        print(f"Fecha evento: {evento['fecha_evento']}")
        print(f"Lugar: {evento['lugar']}")
        print(f"Cupo máximo: {evento['cupo_maximo']}")
        print(f"Activo: {'Sí' if evento['activo'] else 'No'}")
        print(f"Descripción: {evento['descripcion'][:100]}...")
        if evento['imagen_path']:
            print(f"Imagen: {evento['imagen_path']}")
        print("-" * 50)

def ver_inscripciones_eventos():
    """Ver inscripciones a eventos"""
    conn = conectar_bd()
    inscripciones = conn.execute('''
        SELECT i.*, u.nombre as usuario_nombre, u.email as usuario_email, 
               e.titulo as evento_titulo
        FROM inscripciones_eventos i
        JOIN usuarios u ON i.usuario_id = u.id
        JOIN eventos e ON i.evento_id = e.id
        ORDER BY i.fecha_inscripcion DESC
    ''').fetchall()
    conn.close()
    
    print("=" * 80)
    print("📝 INSCRIPCIONES A EVENTOS")
    print("=" * 80)
    
    for inscripcion in inscripciones:
        print(f"Usuario: {inscripcion['usuario_nombre']} ({inscripcion['usuario_email']})")
        print(f"Evento: {inscripcion['evento_titulo']}")
        print(f"Fecha inscripción: {inscripcion['fecha_inscripcion']}")
        print("-" * 50)

def buscar_usuario(email):
    """Buscar usuario específico por email"""
    conn = conectar_bd()
    usuario = conn.execute('SELECT * FROM usuarios WHERE email = ?', (email,)).fetchone()
    conn.close()
    
    if usuario:
        print("=" * 80)
        print(f"👤 USUARIO ENCONTRADO: {email}")
        print("=" * 80)
        print(f"ID: {usuario['id']}")
        print(f"Nombre: {usuario['nombre']}")
        print(f"Email: {usuario['email']}")
        print(f"Rol: {usuario['rol']}")
        print(f"Fecha registro: {usuario['fecha_registro']}")
        print(f"Activo: {'Sí' if usuario['activo'] else 'No'}")
    else:
        print(f"❌ Usuario con email '{email}' no encontrado")

def menu_principal():
    """Menú principal para consultas"""
    while True:
        print("\n" + "=" * 80)
        print("🗄️  CONSULTAS BASE DE DATOS - JUNTA VECINAL")
        print("=" * 80)
        print("1. Ver todos los usuarios")
        print("2. Ver estadísticas de denuncias")
        print("3. Ver denuncias detalladas")
        print("4. Ver noticias")
        print("5. Ver eventos")
        print("6. Ver inscripciones a eventos")
        print("7. Buscar usuario por email")
        print("8. Salir")
        print("-" * 80)
        
        opcion = input("Selecciona una opción (1-8): ").strip()
        
        if opcion == "1":
            ver_todos_usuarios()
        elif opcion == "2":
            ver_estadisticas_denuncias()
        elif opcion == "3":
            ver_denuncias_detalladas()
        elif opcion == "4":
            ver_noticias()
        elif opcion == "5":
            ver_eventos()
        elif opcion == "6":
            ver_inscripciones_eventos()
        elif opcion == "7":
            email = input("Ingresa el email del usuario: ").strip()
            buscar_usuario(email)
        elif opcion == "8":
            print("👋 ¡Hasta luego!")
            break
        else:
            print("❌ Opción no válida")
        
        input("\nPresiona Enter para continuar...")

if __name__ == "__main__":
    menu_principal()

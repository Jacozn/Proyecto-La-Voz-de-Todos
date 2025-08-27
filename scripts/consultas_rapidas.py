import sqlite3

def consultas_rapidas():
    """Consultas rápidas para verificar datos"""
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    
    print("🔍 CONSULTAS RÁPIDAS")
    print("=" * 50)
    
    # Contar usuarios por rol
    print("👥 USUARIOS POR ROL:")
    roles = conn.execute('''
        SELECT rol, COUNT(*) as cantidad 
        FROM usuarios 
        GROUP BY rol
    ''').fetchall()
    
    for rol in roles:
        print(f"  - {rol['rol']}: {rol['cantidad']} usuarios")
    
    # Últimos usuarios registrados
    print("\n📅 ÚLTIMOS 5 USUARIOS REGISTRADOS:")
    ultimos = conn.execute('''
        SELECT nombre, email, rol, fecha_registro 
        FROM usuarios 
        ORDER BY fecha_registro DESC 
        LIMIT 5
    ''').fetchall()
    
    for usuario in ultimos:
        print(f"  - {usuario['nombre']} ({usuario['rol']}) - {usuario['fecha_registro']}")
    
    # Estado de denuncias
    print("\n📊 DENUNCIAS POR ESTADO:")
    estados = conn.execute('''
        SELECT estado, COUNT(*) as cantidad 
        FROM denuncias 
        GROUP BY estado
    ''').fetchall()
    
    for estado in estados:
        print(f"  - {estado['estado']}: {estado['cantidad']}")
    
    # Total de contenido
    print("\n📈 RESUMEN GENERAL:")
    totales = {
        'usuarios': conn.execute('SELECT COUNT(*) as total FROM usuarios').fetchone()['total'],
        'denuncias': conn.execute('SELECT COUNT(*) as total FROM denuncias').fetchone()['total'],
        'noticias': conn.execute('SELECT COUNT(*) as total FROM noticias WHERE activa = 1').fetchone()['total'],
        'eventos': conn.execute('SELECT COUNT(*) as total FROM eventos WHERE activo = 1').fetchone()['total'],
    }
    
    for tipo, cantidad in totales.items():
        print(f"  - {tipo.capitalize()}: {cantidad}")
    
    conn.close()

if __name__ == "__main__":
    consultas_rapidas()

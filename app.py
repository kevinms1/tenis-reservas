from flask import Flask, render_template, request, jsonify
import sqlite3
from datetime import datetime, timedelta
import psycopg2 # Cambiamos sqlite3 por psycopg2
from psycopg2.extras import RealDictCursor
import os

USUARIOS_PERMITIDOS = [
    "cpinedo", "fgallardo", "jsouza", "edante", "gmenacho", "rmodesto", 
    "a castillo", "lseijas", "agodoy", "jsangama", "ycampaña", "jcastillo", 
    "luehara", "fvelez", "rbarriga", "wburgos", "wortega", "emendoza", 
    "hsoriano", "kdibos", "cdávila", "egarcia", "jpadilla", "jcatalan", 
    "jstrella", "achan", "jsalas", "kmelendez"
]


app = Flask(__name__)

def get_db():
    # Render nos dará la URL en una "Variable de Entorno" por seguridad
    DATABASE_URL = os.environ.get('DATABASE_URL') 
    
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    
    # Crear la tabla si no existe (Sintaxis Postgres)
    with conn.cursor() as cur:
        cur.execute('''
            CREATE TABLE IF NOT EXISTS reservas (
                id SERIAL PRIMARY KEY,
                dia TEXT NOT NULL,
                hora TEXT NOT NULL,
                nombre TEXT NOT NULL,
                UNIQUE(dia, hora)
            )
        ''')
    conn.commit()
    return conn

@app.route("/")
def index():
    week_offset = int(request.args.get("week", 0))
    today = datetime.today()
    manana = today + timedelta(days=1)
    
    # Calculamos el inicio de la semana (Lunes)
    monday = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)

    # Diccionario de traducción
    dias_espanol = {
        "Monday": "Lunes",
        "Tuesday": "Martes",
        "Wednesday": "Miércoles",
        "Thursday": "Jueves",
        "Friday": "Viernes",
        "Saturday": "Sábado",
        "Sunday": "Domingo"
    }

    days = []
    for i in range(7):
        day = monday + timedelta(days=i)
        dia_ingles = day.strftime("%A")  # Obtiene el nombre en inglés
        days.append({
            "label": dias_espanol.get(dia_ingles, dia_ingles), # Traduce usando el diccionario
            "date": day.strftime("%d/%m"),
            "key": day.strftime("%Y-%m-%d")
        })

    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT dia, hora, nombre FROM reservas")
    data = cur.fetchall()

    reservas = {}
    for row in data:
        reservas[f"{row['dia']}-{row['hora']}"] = row['nombre']

    return render_template(
        "index.html",
        reservas=reservas,
        days=days,
        week_offset=week_offset,
        hoy_key=today.strftime("%Y-%m-%d"),    # <--- Agregar esto
        manana_key=manana.strftime("%Y-%m-%d") # <--- Agregar esto
    )

@app.route("/reservar", methods=["POST"])
def reservar():
    data = request.json
    nombre_input = data.get("nombre", "").strip().lower()
    dia_reserva = data.get("dia")   # Formato 'YYYY-MM-DD'
    hora_reserva = data.get("hora") # Formato 'H:00'

    # 1. VALIDACIÓN DE LISTA BLANCA
    if nombre_input not in USUARIOS_PERMITIDOS:
        return jsonify({
            "status": "error", 
            "message": "❌ Tu nombre no está en la lista de jugadores autorizados."
        }), 403
    
    # 2. VALIDACIÓN DE REGLA DE 5 HORAS
    conn = get_db()
    cur = conn.cursor()
    
    try:
        # Buscamos la última reserva de este usuario
        cur.execute("""
            SELECT dia, hora FROM reservas 
            WHERE LOWER(nombre) = %s 
            ORDER BY dia DESC, hora DESC LIMIT 1
        """, (nombre_input,))
        
        ultima_reserva = cur.fetchone()

        if ultima_reserva:
            # Convertimos la fecha y hora de la última reserva a un objeto datetime
            # Asumimos que hora viene como '6:00', '10:00', etc.
            fecha_ult = datetime.strptime(f"{ultima_reserva['dia']} {ultima_reserva['hora']}", "%Y-%m-%d %H:%M")
            
            # Calculamos cuándo se libera el bloqueo (Hora de reserva + 5 horas)
            momento_liberacion = fecha_ult + timedelta(hours=5)
            ahora = datetime.now()

            if ahora < momento_liberacion:
                tiempo_restante = momento_liberacion - ahora
                horas_faltan = int(tiempo_restante.total_seconds() // 3600)
                minutos_faltan = int((tiempo_restante.total_seconds() % 3600) // 60)
                
                return jsonify({
                    "status": "error", 
                    "message": f"⏳ Regla anti-acaparamiento: Debes esperar 5h desde tu última reserva. Podrás reservar de nuevo en {horas_faltan}h {minutos_faltan}min."
                }), 403

        # Si pasa todas las reglas, procedemos a insertar
        cur.execute("INSERT INTO reservas (dia, hora, nombre) VALUES (%s, %s, %s)", 
                   (dia_reserva, hora_reserva, data.get("nombre").strip()))
        conn.commit()
        return jsonify({"status": "ok"})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cur.close()
        conn.close()




@app.route("/liberar", methods=["POST"]) # MUEVE ESTO AQUÍ (Arriba del if __name__)
def liberar():
    data = request.json
    password_usuario=data.get("password")

    if password_usuario != "7770":
        return jsonify({"status": "error", "message": "Contraseña incorrecta"}), 403
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM reservas WHERE dia=%s AND hora=%s", (data["dia"], data["hora"]))
        conn.commit()
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    app.run()

 
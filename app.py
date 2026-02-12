from flask import Flask, render_template, request, jsonify
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)

def get_db():
    # check_same_thread=False es necesario para Flask + SQLite
    conn = sqlite3.connect("reservas.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row # Permite acceder por nombre de columna
    return conn

@app.route("/")
def index():
    week_offset = int(request.args.get("week", 0))
    today = datetime.today()
    manana = today + timedelta(days=1)
    
    # Calculamos el inicio de la semana (Lunes)
    monday = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)

    days = []
    for i in range(7):
        day = monday + timedelta(days=i)
        days.append({
            "label": day.strftime("%A"), # Nota: saldrá en inglés según tu OS
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
    
    # Validación simple de seguridad: No permitir reservar con más de 24h de antelación
    # (Opcional, ya que el JS lo filtrará, pero bueno tenerlo en el servidor)
    fecha_reserva = datetime.strptime(data["dia"] + " " + data["hora"], "%Y-%m-%d %H:%M")
    if fecha_reserva > datetime.now() + timedelta(hours=24):
        return jsonify({"status": "error", "message": "Solo puedes reservar con 24h de antelación"}), 400

    db = get_db()
    cur = db.cursor()
    try:
        cur.execute("INSERT INTO reservas (dia, hora, nombre) VALUES (?, ?, ?)", 
                   (data["dia"], data["hora"], data["nombre"]))
        db.commit()
        return jsonify({"status": "ok"})
    except sqlite3.IntegrityError:
        return jsonify({"status": "error", "message": "Ya está ocupado"}), 400

@app.route("/liberar", methods=["POST"]) # MUEVE ESTO AQUÍ (Arriba del if __name__)
def liberar():
    data = request.json
    db = get_db()
    cur = db.cursor()
    cur.execute("DELETE FROM reservas WHERE dia=? AND hora=?", (data["dia"], data["hora"]))
    db.commit()
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run()

 
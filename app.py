from flask import Flask, render_template, request, redirect, url_for, session, flash
import pyodbc
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-me")

# ---------- Selección automática del driver ODBC ----------
drivers = pyodbc.drivers()
sql_drivers = [d for d in drivers if "SQL Server" in d]
if sql_drivers:
    DB_DRIVER = "{" + sql_drivers[-1] + "}"
else:
    raise RuntimeError("No se encontró un driver ODBC de SQL Server instalado.")

# ---------- Configuración de la BD ----------
DB_SERVER = os.environ.get("DB_SERVER", ".\SQLEXPRESSNEW")
DB_DATABASE = os.environ.get("DB_DATABASE", "SistemaInventario")
DB_USER = os.environ.get("DB_USER", "sa")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "mezasql")

def get_connection():
    conn_str = (
        f"DRIVER={DB_DRIVER};"
        f"SERVER={DB_SERVER};"
        f"DATABASE={DB_DATABASE};"
        f"UID={DB_USER};"
        f"PWD={DB_PASSWORD};"
        "TrustServerCertificate=yes;"
    )
    return pyodbc.connect(conn_str)

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_email" not in session:
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return wrapper

@app.route("/", methods=["GET", "POST"])
def index():
    error = None
    if request.method == "POST":
        correo = request.form.get("correo", "").strip()
        contrasena = request.form.get("contrasena", "")
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT email 
                        FROM Usuarios 
                        WHERE email = ? AND contrasena = ?
                    """, (correo, contrasena))
                    row = cur.fetchone()
            if row:
                session["user_email"] = row[0]
                return redirect(url_for("inventario"))
            else:
                error = "Credenciales incorrectas."
        except Exception as e:
            error = f"Error de conexión/consulta: {e}"
    return render_template("index.html", error=error)

@app.route("/inventario")
@login_required
def inventario():
    productos = []
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        id_producto, nombre, descripcion, cantidad, activo, fecha_creacion, fecha_modificacion
                    FROM Productos
                    ORDER BY id_producto
                """)
                for row in cur.fetchall():
                    productos.append({
                        "id_producto": row[0],
                        "nombre": row[1],
                        "descripcion": row[2],
                        "cantidad": row[3],
                        "activo": row[4],
                        "fecha_creacion": row[5],
                        "fecha_modificacion": row[6],
                    })
    except Exception as e:
        flash(f"Error al obtener productos: {e}", "error")
    return render_template("inventario.html", productos=productos, user=session.get("user_email"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

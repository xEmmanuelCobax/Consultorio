from flask import Flask, render_template
import mariadb, json

app = Flask(__name__)
app.config['DEBUG'] = True

# cmd admin privileges
# net start/stop MariaDB
config = {
    'host': '127.0.0.1',
    'port': 3307,
    'user': 'root',
    'password': 'super',
    'database': 'karate'
}

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/dashboard', methods=['GET'])
def dashboard():
    return render_template('dashboard.html')


@app.route("/Registrarse", methods=["GET"])
def Registrarse():
    return render_template("Registrarse.html")


@app.route("/Ingreso", methods=["GET"])
def Ingreso():
    return render_template("Ingreso.html")


@app.route("/template", methods=["GET"])
def template():
    return render_template("Template.html")


@app.route("/Agenda", methods=["GET"])
def Agenda():
    return render_template("Agenda.html")


@app.route("/Pacientes", methods=["GET"])
def Pacientes():
    return render_template("Pacientes.html")


@app.route("/Inventario", methods=["GET"])
def Inventario():
    return render_template("Inventario.html")


@app.route("/Ajustes", methods=["GET"])
def Ajustes():
    return render_template("Ajustes.html")


@app.route("/Inicio", methods=["GET"])
def Inicio():
    return render_template("Inicio.html")


@app.route("/Índice", methods=["GET"])
def Índice():
    return render_template("Índice.html")


@app.route("/Registrar_Paciente", methods=["GET"])
def Registrar_Paciente():
    return render_template("Registrar_Paciente.html")


app.run()

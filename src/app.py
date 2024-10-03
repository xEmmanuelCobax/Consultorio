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


@app.route("/SignUp", methods=["GET"])
def SignUp():
    return render_template("SignIn.html")


@app.route("/SignIn", methods=["GET"])
def SignIn():
    return render_template("SignUp.html")


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


app.run()

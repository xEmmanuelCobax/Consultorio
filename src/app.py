from flask import Flask, render_template
import mariadb, json

app = Flask(__name__)
app.config['DEBUG'] = True

# Metodo para poder realizar CUD> CREATE, UPDATE Y DELETE
def CUD(query, params=None):
    print("<-------------------- Conectando... --------------------")
    try:
        # Conectar a la BD
        connection = mariadb.connect(
            host="localhost",  # Cambia por tu host si es diferente
            user="root",  # Usuario de MariaDB
            password="123",  # Contraseña de MariaDB
            database="braindamage",  # Nombre de la base de datos
        )
        cursor = connection.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        connection.commit()  # Confirmar los cambios en la base de datos
        print("<-------------------- Conexión exitosa --------------------")
    except Exception as ex:
        print(f"<-------------------- Error: {ex} -------------------->")
    finally:
        connection.close()
        print("-------------------- Conexión finalizada -------------------->")

def Read(query, params=None):
    print("<-------------------- Conectando... --------------------")
    connection = None
    try:
        connection = mariadb.connect(
            host="localhost",  # Cambia por tu host si es diferente
            user="root",  # Usuario de MariaDB
            password="123",  # Contraseña de MariaDB
            database="braindamage",  # Nombre de la base de datos
        )
        cursor = connection.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        rows = cursor.fetchall()
        results = [list(row) for row in rows]  # Convert each row to a list
        print("<-------------------- Conexión exitosa --------------------")

        print('Columns:')
        for column in cursor.description:
            print(column)

        for result in results:
            print(result)
        print("---------------------------------------->")
        return results
    except Exception as ex:
        results = False
        print(f"<-------------------- Error: {ex} -------------------->")
        return None
    finally:
        if connection:
            connection.close()
            print("-------------------- Conexión finalizada -------------------->")

### Estos son los antiguos
# Los nuevos inicias desde /Inicio w
@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/dashboard', methods=['GET'])
def dashboard():
    query = "SELECT * FROM pacientes JOIN datos_basicos ON pacientes.ID_Datos_Basicos = datos_basicos.ID_Datos_Basicos"
    pacientes = Read(query)  # Llama a Read con la consulta adecuada
    print("Datos consulta 1")

    query = """
        select * FROM Citas 
        JOIN Estatus_cita ON citas.ID_estatus_cita = Estatus_cita.ID_estatus_cita
        JOIN Pacientes ON citas.ID_paciente = Pacientes.ID_paciente
        JOIN Doctores ON Doctores.ID_doctor = Citas.ID_doctor
    """
    params = ()
    records = Read(query, params)
    print('$$$ testeando joins $$$')
    for record in records:
        print(record)

    return render_template('dashboard.html', pacientes=pacientes)

# Estos son nuevos
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
    query = "SELECT * FROM pacientes JOIN datos_basicos ON pacientes.ID_Datos_Basicos = datos_basicos.ID_Datos_Basicos"
    pacientes = Read(query)  # Llama a Read con la consulta adecuada
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

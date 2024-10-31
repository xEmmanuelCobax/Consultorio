from flask import (
    Flask,
    render_template,
    request,
    session,
    redirect,
    url_for,
    jsonify,
    abort,
    flash,
)
import mariadb, utils, datetime, threading, secrets, time, logging, os
from config import ROOT_CONECTION
from models import Usuario
from flask_login import (
    login_manager,
    LoginManager,
    current_user,
    login_user,
    logout_user,
    login_required,
)
from flask_socketio import SocketIO
from flask_limiter import Limiter
from datetime import datetime, timedelta


"""
TODO: 
1. Hacer el crud para agregar recetas a las citas
2. Ah sí, hacer validaciones en el front robustas con javascript
3. Manejar la concurrencia, que cuando el doctor esté modificando una cita, la recepcionista se le bloquee la opción de hacer algo ???
Si, literal se bloquea?, xD, esta raro pero ok, vava
Algo así nos dijo sákura después de la charla de la psicóloga
Le daremos prioridad al doctor, así si los dos modifican la misma cita, la recepcionista no deberá poder hacerlo
"""

# region app

app = Flask(__name__)
socketio = SocketIO(app=app)
limiter = Limiter(key_func=lambda: request.path, app=app)
app.config["DEBUG"] = True
app.secret_key = "super secret key"

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "Ingreso"

# endregion


@app.template_global('getcurdate')
def getcurdate():
    curdate = datetime.now()
    return f'{curdate.year}-{curdate.month}-{curdate.day}'

@app.template_global('curdateminusdelta')
def curdateminusdelta(days):
    curdate = datetime.now() #6574
    fecha = curdate - timedelta(days=days)
    return f'{fecha.year}-{str(fecha.month).zfill(2)}-{str(fecha.day).zfill(2)}'

# region Locks

lock_agregar_pacientes = threading.Lock()
lock_modificar_pacientes = threading.Lock()
lock_eliminar_pacientes = threading.Lock()
lock_agregar_medicamento = threading.Lock()
lock_modificar_medicamento = threading.Lock()
lock_eliminar_medicamento = threading.Lock()
lock_agregar_cita = threading.Lock()
lock_modificar_cita = threading.Lock()
lock_eliminar_cita = threading.Lock()

# endregion

# region Logs

os.makedirs("logs", exist_ok=True)
fecha_actual = datetime.now().strftime("%d-%m-%Y")
nombre_archivo_log = f"logs/app-{fecha_actual}.log"  # Ruta actualizada
# Configuración del logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(nombre_archivo_log, mode="a"),  # Modo de adición
        logging.StreamHandler(),  # Mostrar en la consola
    ],
)
logging.getLogger("werkzeug").setLevel(logging.WARNING)

# endregion

# region SocketIO

# Aquí se define el diccionario con los botones para las vistas de pacientes, citas(agenda) e inventario(medicinas)
button_states = {
    'Pacientes': {'agregar': False, 'modificar': False, 'eliminar': False},
    'Citas': {'agregar': False, 'modificar': False, 'eliminar': False},
    'Inventario': {'agregar': False, 'modificar': False, 'eliminar': False},
}

# Con este pequeño diccionario se guarda los locks enviados por un cliente, para que en caso de desconectarse, se desbloqueen los botones
# que haya podido estar bloqueando al momento de desconectarse.
client_locks = {}

# Con este método se bloquean los botones.
@socketio.on('lock_button')
def lock_button(data):
    client_id = request.sid
    print(f'Lock by ID cliente: {client_id}')

    view = data.get('view')
    action = data.get('action')
    if view in button_states and action in button_states[view]:
        button_states[view][action] = True

        # Registrar el bloqueo del cliente
        if client_id not in client_locks:
            client_locks[client_id] = []
        client_locks[client_id].append((view, action))

        socketio.emit('lock', {'view': view, 'action': action, 'status': True})

# Con este método se desbloquean los botones.
@socketio.on('unlock_button')
def unlock_button(data):
    client_id = request.sid
    print(f'Unlock by ID cliente: {client_id}: liberar {data.get('view')}')
    view = data.get('view')
    action = data.get('action')
    if view in button_states and action in button_states[view]:
        button_states[view][action] = False
        socketio.emit('lock', {'view': view, 'action': action, 'status': False})

# Con este método se obtiene el ID del usuario al conectarse a cualquiera de las páginas con conexión SocketIO.
@socketio.on('connect')
def handle_connect():
    print('Un cliente se ha conectado:', request.sid)

# Con este método se obtiene el ID del usuario al desconectarse a cualquiera de las páginas con conexión SocketIO,
# Además, se encarga de desbloquear cualquier botón bloqueado por el usuario al momento de desconectarse.
@socketio.on('disconnect')
def handle_disconnect():
    client_id = request.sid
    print(f'Se desconectó ID cliente: {client_id}')
    # Desbloquear los botones que este cliente bloqueó
    if client_id in client_locks:
        for view, action in client_locks[client_id]:
            button_states[view][action] = False
            socketio.emit('lock', {'view': view, 'action': action, 'status': False})
        
        # Eliminar el cliente de la lista de bloqueos
        del client_locks[client_id]

# Este método solicita el estado de los botones.
@socketio.on('request_button_states')
def request_button_states(data):
    view = data.get('view')
    if view in button_states:
        event_name = f'update_{view}_states'
        socketio.emit(event_name, button_states[view])

# endregion

# Esta función es para que flask-login recupere el usuario loggeado cuando una ruta tiene @login_required
@login_manager.user_loader
def load_user(id: int):
    # Si ya inició sesión, se guarda el tipo de usuario y se recupera
    role_usuario = session.get("Tipo_usuario")
    if role_usuario is None:
        return None
    print(f"Rol de usuario actual: {role_usuario}")

    conn = mariadb.connect(**ROOT_CONECTION)
    if conn is not None:
        cursor = conn.cursor(dictionary=True)
        # region ternarios
        tabla = (
            "admin"
            if role_usuario == "admin"
            else (
                "doctores"
                if role_usuario == "doctor"
                else "recepcionistas" if role_usuario == "recepcionista" else "none"
            )
        )
        nombre_PK = (
            "ID_admin"
            if role_usuario == "admin"
            else (
                "ID_doctor"
                if role_usuario == "doctor"
                else "ID_recepcionista" if role_usuario == "recepcionista" else "none"
            )
        )
        query = f"""
            SELECT * FROM {tabla} 
            JOIN datos_basicos ON datos_basicos.ID_datos_basicos = {tabla}.ID_datos_basicos
            WHERE {nombre_PK}
        """
        # endregion
        cursor.execute(query)
        result = cursor.fetchone()
        if result is not None:
            utils.print_cols(result)
            usuario = Usuario(
                id=id,
                tipo_usuario=role_usuario,
                id_datos_basicos=result["ID_Datos_Basicos"],
                nombres=result["Nombres"],
                ap_pat=result["Apellido_Paterno"],
                ap_mat=result["Apellido_Materno"],
            )
            return usuario
    return None


@app.errorhandler(401)
def error():
    return "<h1>ACCESO PROHIBIDO</h1>"

# region CUD

# Metodo para poder realizar CUD> CREATE, UPDATE Y DELETE
def CUD(query, params=None):
    print("<-------------------- Conectando... --------------------")
    try:
        # Conectar a la BD
        connection = mariadb.connect(**current_user.Conection)
        cursor = connection.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        connection.commit()  # Confirmar los cambios en la base de datos
        print("<-------------------- Conexión exitosa --------------------")
    except Exception as ex:
        if connection:
            connection.rollback()
        print(f"<-------------------- Error: {ex} -------------------->")
    finally:
        if connection:
            connection.close()
        print("-------------------- Conexión finalizada -------------------->")

# endregion

# region Read

def Read(query, params=None):
    print("<-------------------- Conectando... --------------------")
    connection = None
    try:
        connection = mariadb.connect(**current_user.Conection)
        cursor = connection.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        rows = cursor.fetchall()

        results = [list(row) for row in rows]  # Convert each row to a list
        print("<-------------------- Conexión exitosa --------------------")

        # print('Columns:')
        # for column in cursor.description:
        #     print(f'{type(column)} - {column}')

        # for result in results:
        #     print(f'{type(result)} - {result}')
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

# endregion

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


# region registro
@app.route("/Registrarse", methods=["GET"])
def Registrarse():
    if current_user.is_authenticated:
        flash('Ya haz iniciado sesión')
        print('Ya haz iniciado sesión')
        return redirect(url_for("Inicio"))
    if request.method == 'POST':
        nombres = request.form.get('nombres')
        ap_p = request.form.get('apellidoPaterno')
        ap_m = request.form.get('apellidoMaterno')
        telefono = request.form.get('telefono')
        email = request.form.get('email')
        rfc = request.form.get('rfc')
        cedula = request.form.get('cedula')
        password = request.form.get('password')
        fecha_nacimiento = request.form.get('fechaNacimiento')
        registro_doctor = request.form.get('registro-doctor')

        conn = mariadb.connect(**ROOT_CONECTION)
        if conn is not None:
            conn.autocommit = False
            try:
                cursor = conn.cursor(dictionary=True)
                insertar_datos_basicos = """
                    INSERT INTO datos_basicos 
                    (Nombres, Apellido_Paterno, Apellido_Materno, Email, Fecha_Nacimiento, Telefono)
                    VALUES (?, ?, ?, ?, ?, ?)
                """
                datos_basicos = (nombres, ap_p, ap_m, email, fecha_nacimiento, telefono)
                cursor.execute(insertar_datos_basicos, datos_basicos)
                id_datos_basicos = cursor.lastrowid

                if registro_doctor is None:
                    insertar_recepcionista = """
                        INSERT INTO recepcionistas
                        (ID_datos_basicos, RFC, Contraseña)
                        VALUES (?, ?, ?)
                    """
                    recepcionista = (id_datos_basicos, rfc, password)
                    cursor.execute(insertar_recepcionista, recepcionista)
                elif registro_doctor == 1:
                    insertar_doctor = """
                        INSERT INTO doctores
                        (ID_datos_basicos, RFC, Contraseña, Cedula_Profesional)
                        VALUES (?, ?, ?, ?)
                    """
                    doctor = (id_datos_basicos, rfc, password, cedula)
                    cursor.execute(insertar_doctor, doctor)
                else:
                    raise Exception('Formulario inválido')
                conn.commit()
                return redirect(url_for('Ingreso'))
            except Exception as e:
                print(f'Error: {e}')
                conn.rollback()
            finally:
                conn.close()
    return render_template("Registrarse.html")


@app.route("/Ingreso", methods=["GET"])
def Ingreso():
    print(current_user)
    print(current_user.is_authenticated)
    # Redireccionar
    if current_user.is_authenticated:
        flash("Ya haz iniciado sesión")
        print("Ya haz iniciado sesión")
        return redirect(url_for("Inicio"))

    # Solicitar datos
    return render_template("Ingreso.html")

# region login

active_sessions = {
    'doctores': {},
    'recepcionistas': {}
}

@app.route("/iniciar_sesion", methods=["POST"])
def logearse():
    if current_user.is_authenticated:
        print("FORBIDDEN")
        flash('Mensaje de error ',  'error')
        return redirect(url_for("Inicio"))

    tipo_sesion = request.form.get("elegir_sesion")

    if tipo_sesion == "doctor":
        cedula = request.form.get("cedula-doctor")
        password = request.form.get("password")
        print(f"Iniciar sesion el doctor:\n{cedula}\n{password}")
        conn = mariadb.connect(**ROOT_CONECTION)
        if conn:
            try:
                usuario_existe = """
                    SELECT * FROM doctores
                    JOIN datos_basicos ON doctores.ID_datos_basicos = datos_basicos.ID_datos_basicos
                    WHERE Cedula_Profesional = ? AND Contraseña = ?
                    """
                params = (
                    cedula,
                    password,
                )

                cursor = conn.cursor(dictionary=True)
                cursor.execute(usuario_existe, params)
                result = cursor.fetchone()
                if result is not None:
                    # utils.print_cols(result)
                    # Aquí logeamos al usuario con flask-login
                    ID_Doctor = str(result["ID_Doctor"])
                    if ID_Doctor in active_sessions['doctores']:  
                        print("Ya hay una sesión activa para este doctor.")
                        flash(" Ya hay una sesión activa para este doctor.")
                        return redirect(url_for("Ingreso"))
                    usuario = Usuario(
                        id=result["ID_Doctor"],
                        tipo_usuario=tipo_sesion,
                        id_datos_basicos=result["ID_Datos_Basicos"],
                        nombres=result["Nombres"],
                        ap_pat=result["Apellido_Paterno"],
                        ap_mat=result["Apellido_Materno"],
                    )
                    print(usuario)
                    login_user(usuario)
                    active_sessions['doctores'][ID_Doctor] = ID_Doctor
                    # También guardamos datos en la sesión
                    # session.clear()
                    session["Tipo_usuario"] = "doctor"
                    session["ID_doctor"] = result["ID_Doctor"]
                    session["ID_datos_basicos"] = result["ID_Datos_Basicos"]
                    session["Nombres"] = result["Nombres"]
                    session["Apellido_Paterno"] = result["Apellido_Paterno"]
                    session["Apellido_Materno"] = result["Apellido_Materno"]
                    session['token'] = secrets.token_hex(16)
            except:
                conn.rollback()
            finally:
                conn.close()
            pass
    elif tipo_sesion == "recepcionista":
        rfc = request.form.get("rfc-recepcionista")
        password = request.form.get("password")
        print(f'Iniciar sesion la recepcionista:\n{rfc}\n{password}')
        conn = mariadb.connect(**ROOT_CONECTION)
        if conn:
            try:
                usuario_existe = """
                    SELECT * FROM recepcionistas
                    JOIN datos_basicos ON recepcionistas.ID_datos_basicos = datos_basicos.ID_datos_basicos
                    WHERE RFC = ? AND Contraseña = ?
                    """
                params = (
                    rfc,
                    password,
                )
                cursor = conn.cursor(dictionary=True)
                cursor.execute(usuario_existe, params)
                result = cursor.fetchone()
                if result is not None:
                    utils.print_cols(result)
                    # Aquí se logea la recepcionista
                    ID_Recepcionista = str(result["ID_Recepcionista"])
                    if ID_Recepcionista in active_sessions['recepcionistas']:  
                        print("Ya hay una sesión activa para esta recepcionista.")
                        flash(" Ya hay una sesión activa para este doctor.")
                        return redirect(url_for("Inicio"))
                    usuario = Usuario(
                        id=result["ID_Recepcionista"],
                        tipo_usuario=tipo_sesion,
                        id_datos_basicos=result["ID_Datos_Basicos"],
                        nombres=result["Nombres"],
                        ap_pat=result["Apellido_Paterno"],
                        ap_mat=result["Apellido_Materno"],
                    )
                    print(usuario)
                    login_user(usuario)
                    active_sessions['recepcionistas'][ID_Recepcionista] = ID_Recepcionista
                    # Se guardan datos en la session
                    # session.clear()
                    session["Tipo_usuario"] = "recepcionista"
                    session["ID_recepcionista"] = result["ID_Recepcionista"]
                    session["ID_datos_basicos"] = result["ID_Datos_Basicos"]
                    session["Nombres"] = result["Nombres"]
                    session["Apellido_Paterno"] = result["Apellido_Paterno"]
                    session["Apellido_Materno"] = result["Apellido_Materno"]
                    session['token'] = secrets.token_hex(16)
                    print(tipo_sesion)
            except:
                conn.rollback()
            finally:
                conn.close()
            pass

    else:
        print("error")

    return redirect(url_for("Inicio"))

# endregion

# region logout

@app.route("/logout", methods=["GET"])
@login_required
def logout():

    if "Tipo_usuario" not in session:
        print("FORBIDEN")
        return redirect(url_for("Inicio"))

    user = current_user

    if isinstance(user, Usuario):
        role = user.Tipo_usuario
        nombres = user.Nombres
        apellido_p = user.Apellido_Paterno
        if role == "doctor":
            ID = str(session.get("ID_doctor"))
            print(active_sessions)
            if ID in active_sessions['doctores']:
                del active_sessions['doctores'][ID]
                print(f"ID DOCTOR LOGOUT: {ID}")
        elif role == "recepcionista":
            ID = str(session.get("ID_recepcionista"))
            if ID in active_sessions['recepcionistas']:
                del active_sessions['recepcionistas'][ID]
                print(f"ID RECEPCIONISTA LOGOUT: {ID}")
        print(
            f"Se cerró la sesión del {role} {nombres} {apellido_p} por el bien de la humanidad"
        )
    logout_user()
    session.clear()
    return redirect(url_for("Inicio"))


# endregion

# region Agenda
@app.route("/Agenda", methods=["GET"])
@login_required
def Agenda():
    conn = mariadb.connect(**current_user.Conection)
    if conn:
        try:
            query = """
                SELECT datos_p.Nombres, datos_p.Apellido_Paterno, datos_p.Apellido_Materno,
                    Fecha, Motivo,
                    datos_d.Nombres AS Nombres_doctor, datos_d.Apellido_Paterno AS Apellido_p_doctor, datos_d.Apellido_Materno AS Apellido_m_doctor,
                    datos_r.Nombres AS Nombres_recep, datos_r.Apellido_Paterno AS Apellido_p_recep, datos_r.Apellido_Materno AS Apellido_m_recep
                FROM citas
                JOIN estatus_cita ON citas.ID_Estatus_Cita = estatus_cita.ID_Estatus_Cita
                #Paciente y sus datos
                JOIN pacientes ON citas.ID_Paciente = pacientes.ID_Paciente
                    JOIN datos_basicos AS datos_p ON pacientes.ID_Datos_Basicos = datos_p.ID_Datos_Basicos
                #Doctor y sus datos
                JOIN doctores ON citas.ID_Doctor = doctores.ID_Doctor
                    JOIN datos_basicos AS datos_d ON doctores.ID_Datos_Basicos = datos_d.ID_Datos_Basicos
                #Recepcionista y sus datos
                JOIN recepcionistas ON citas.ID_Recepcionista = recepcionistas.ID_Recepcionista
                    JOIN datos_basicos AS datos_r ON recepcionistas.ID_Datos_Basicos = datos_r.ID_Datos_Basicos
                """
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query)
            rows = cursor.fetchall()

            print("Cita:")
            # print(utils.print_rows(rows))

            query_lista_pacientes = """
                SELECT ID_paciente, Nombres, Apellido_paterno, Apellido_materno FROM pacientes
                JOIN datos_basicos ON datos_basicos.ID_datos_basicos = pacientes.ID_datos_basicos
                """
            cursor.execute(query_lista_pacientes)
            lista_pacientes = cursor.fetchall()
            print("Pacientes")
            # print(utils.print_rows(lista_pacientes))

            query_lista_doctores = """
                SELECT ID_doctor, Nombres, Apellido_paterno, Apellido_materno FROM doctores
                JOIN datos_basicos ON datos_basicos.ID_datos_basicos = doctores.ID_datos_basicos
                """
            cursor.execute(query_lista_doctores)
            lista_doctores = cursor.fetchall()
            print("Doctores")
            # print(utils.print_rows(lista_doctores))
        except:
            pass
        finally:
            conn.close()
    return render_template(
        "Agenda.html",
        citas=rows,
        lista_pacientes=lista_pacientes,
        lista_doctores=lista_doctores,
        current_page="Agenda",
    )
# endregion

# region pacientes
@app.route("/Pacientes", methods=["GET"])
@login_required
def Pacientes():
    query = "SELECT * FROM pacientes JOIN datos_basicos ON pacientes.ID_Datos_Basicos = datos_basicos.ID_Datos_Basicos"
    pacientes = Read(query)  # Llama a Read con la consulta adecuada
    return render_template(
        "Pacientes.html", pacientes=pacientes, current_page="Pacientes"
    )


@app.route("/Agregar_Pacientes", methods=["POST"])
@login_required
@limiter.limit("10 per minute")
def agregar_Pacientes():
    user_token = session['token']
    request_token = request.form.get('token_agregar')
    if request_token != user_token:
        app.logger.warning("Intento de acceso a la funcion de agregar pacientes de usuario no autenticado.")
        return jsonify({'message': 'FORBIDDEN: NO AUTENTICADO'}), 403
    if lock_agregar_pacientes.locked():
        app.logger.warning("Intento de acceso a la funcion de agregar pacientes mientras se encontraba en uso (blocked).")
        return jsonify({'message': 'BLOQUEADO: FUNCIÓN EN USO'}), 423
    try:
        with lock_agregar_pacientes:
            # Solicita los datos del forms en Pacientes.html
            app.logger.info("Ejecutando operación de agregar paciente...")
            nombre = request.form["nombre"]
            apellido_p = request.form["apellido_p_paciente"]
            apellido_m = request.form["apellido_m_paciente"]
            email = request.form["email_paciente"]
            telefono = request.form["telefono_paciente"]
            fecha_n = request.form["fecha_n_paciente"]
            direccion = request.form.get("direccion_paciente")

            # Inserta los datos recibidos del forms
            print("<Insertar los datos>")
            insertar_datos_basicos = """
                insert into datos_basicos 
                (nombres, apellido_paterno, apellido_materno, email, telefono, fecha_nacimiento, direccion)
                values
                (?,?,?,?,?,?,?)
                """
            # Coloca los parámetros en una variable y ejecuta la consulta SQL, con esto insertado los datos básicos del paciente
            params = (nombre, apellido_p, apellido_m, email, telefono, fecha_n, direccion)
            CUD(insertar_datos_basicos, params)
            # Realiza una consulta para obtener el último ID insertado dentro de la tabla de datos básicos,
            # esto en base al email y al telefono recientemente insertados
            last_ID = Read(
                """
                SELECT id_datos_basicos from datos_basicos
                WHERE email=? AND telefono=?;
                """,
                (
                    email,
                    telefono,
                ),
            )
            # Imprimir el ID obtenido
            print("LAST ID = ", last_ID)

            # Hacer una ultima consulta para insertar el ID de los datos básicos dentro de la tabla pacientes
            CUD(
                """
                INSERT into pacientes (id_datos_basicos) values (?)
                """,
                (last_ID[0][0],),
            )
            # Imprimir los datos básicos para saber qué se terminó por añadir dentro de la tabla de datos básicos.
            print(f"{nombre} {apellido_p} {apellido_m} {email} {fecha_n} {direccion}")
            request_token = None
            app.logger.info(f"Operacion de agregar paciente {nombre} {apellido_p} {apellido_m} completada correctamente")
    except Exception as e:
        app.logger.error(f'Error en la operación de agregar paciente: {str(e)}')
        return jsonify({'message': f'Error en la operación de agregar paciente: {str(e)}'}), 500
    return redirect(url_for("Pacientes"))


@app.route("/Modificar_Pacientes", methods=["POST"])
@login_required
@limiter.limit("10 per minute")
def modificar_Paciente():
    user_token = session['token']
    request_token = request.form.get('token_modificar')
    if request_token != user_token:
        app.logger.warning("Intento de acceso a la funcion de modificar pacientes de usuario no autenticado.")
        return jsonify({'message': 'FORBIDDEN: NO AUTENTICADO'}), 403
    if lock_modificar_pacientes.locked():
        app.logger.warning("Intento de acceso a la funcion de modificar pacientes mientras se encontraba en uso (blocked).")
        return jsonify({'message': 'BLOQUEADO: FUNCIÓN EN USO'}), 423
    
    try:
        with lock_modificar_pacientes:    
            # Solicita los datos del forms en Pacientes.html
            app.logger.info("Ejecutando operación de modificar paciente...")
            paciente_id = request.form["paciente_id"]
            nombre = request.form["nombre_mod"]
            apellido_p = request.form["apellido_p_paciente_mod"]
            apellido_m = request.form["apellido_m_paciente_mod"]
            email = request.form["email_paciente_mod"]
            telefono = request.form["telefono_paciente_mod"]
            fecha_n = request.form["fecha_n_paciente_mod"]
            direccion = request.form.get("direccion_paciente_mod")

            print("<Consultar la id_paciente>")
            id_datos_basicos = Read(
                """
                SELECT id_datos_basicos FROM pacientes
                WHERE id_paciente=?;
                """,
                (paciente_id,),
            )

            # Imprimir el ID obtenido
            print("ID DATOS BÁSICOS = ", id_datos_basicos)

            # Inserta los datos recibidos del forms
            print("<Modificar los datos>")
            CUD(
                """
                UPDATE datos_basicos 
                SET nombres=?, apellido_paterno=?, apellido_materno=?, email=?, telefono=?, fecha_nacimiento=?, direccion=?
                WHERE id_datos_basicos=?;
            """,
                (
                    nombre,
                    apellido_p,
                    apellido_m,
                    email,
                    telefono,
                    fecha_n,
                    direccion,
                    int(id_datos_basicos[0][0]),
                ),
            )
            # Imprimir los datos básicos para saber qué se terminó por añadir dentro de la tabla de datos básicos.
            print(f"{nombre} {apellido_p} {apellido_m} {email} {fecha_n} {direccion}")
            app.logger.info(f"Operacion de modificar paciente {nombre} {apellido_p} {apellido_m} completada correctamente")
    except Exception as e:
        app.logger.error(f'Error en la operación de modificar paciente: {str(e)}')
        return jsonify({'message': f'Error en la operación de modificar paciente: {str(e)}'}), 500
        
    return redirect(url_for("Pacientes"))


@app.route("/Eliminar_Pacientes", methods=["POST"])
@login_required
@limiter.limit("10 per minute")
def eliminar_Paciente():
    user_token = session['token']
    request_token = request.form.get('token_eliminar')
    if request_token != user_token:
        app.logger.warning("Intento de acceso a la funcion de eliminar pacientes de usuario no autenticado.")
        return jsonify({'message': 'FORBIDDEN: NO AUTENTICADO'}), 403
    if lock_eliminar_pacientes.locked():
        app.logger.warning("Intento de acceso a la funcion de eliminar pacientes mientras se encontraba en uso (blocked).")
        return jsonify({'message': 'BLOQUEADO: FUNCIÓN EN USO'}), 423
    
    try:
        with lock_eliminar_pacientes:    
            # Solicita los datos del forms en Pacientes.html
            app.logger.info("Ejecutando operación de eliminar paciente...")
            paciente_id = request.form["paciente_id_eli"]
            # Consultar la ID_Paciente para obtener la ID en Datos_Básicos
            print("<Consultar la id_datos_basicos>")
            id_datos_basicos = Read(
                """
                SELECT Id_Datos_Basicos FROM pacientes
                WHERE Id_Paciente = ?;
                """,
                (paciente_id,),
            )
            # Imprimir el ID obtenido
            print("ID DATOS BÁSICOS = ", id_datos_basicos[0][0])
            # Borrar los datos en la tabla pacientes y en la tabla dat
            print("<Borrar los datos>")
            CUD(
                """
                DELETE FROM datos_basicos
                WHERE id_datos_basicos=?;
            """,
                (id_datos_basicos[0][0],),
            )
            app.logger.info(f"Operacion de eliminar paciente {nombre} {apellido_p} {apellido_m} completada correctamente")
    except Exception as e:
        app.logger.error(f'Error en la operación de eliminar paciente: {str(e)}')
        return jsonify({'message': f'Error en la operación de eliminar paciente: {str(e)}'}), 500
    return redirect(url_for("Pacientes"))

# endregion


# region Medicamentos
@app.route("/Inventario", methods=["GET"])
@login_required
def Inventario():
    conn = mariadb.connect(**current_user.Conection)
    if conn:
        consultar_medicamentos = """
            SELECT medicamento.ID_Medicamento, medicamento.Nombre AS Nombre_medicamento, proveedores.*
            FROM medicamento
            JOIN proveedores ON proveedores.ID_Proveedor = medicamento.ID_Proveedor
            """
        cursor = conn.cursor(dictionary=True)
        cursor.execute(consultar_medicamentos)
        rows = cursor.fetchall()
        utils.print_rows(rows)

        consultar_proveedores = """
            SELECT ID_proveedor, Nombre
            FROM proveedores
        """
        cursor.execute(consultar_proveedores)
        lista_proveedores = cursor.fetchall()
        # utils.print_rows(lista_proveedores)

    return render_template(
        "Inventario.html",
        medicamentos=rows,
        lista_proveedores=lista_proveedores,
        current_page="Inventario",
    )


@app.route("/agregar_medicamento", methods=["POST"])
@login_required
@limiter.limit("10 per minute")
def agregar_medicamento():
    if request.method == "POST":
        user_token = session['token']
        request_token = request.form.get('token_agregar')
        if request_token != user_token:
            app.logger.warning("Intento de acceso a la funcion de agregar medicina de usuario no autenticado.")
            return jsonify({'message': 'FORBIDDEN: NO AUTENTICADO'}), 403
        if lock_agregar_medicamento.locked():
            app.logger.warning("Intento de acceso a la funcion de agregar medicina mientras se encontraba en uso (blocked).")
            return jsonify({'message': 'BLOQUEADO: FUNCIÓN EN USO'}), 423
        
        try:
            with lock_agregar_medicamento: 
                # region Form
                app.logger.info("Ejecutando operación de agregar medicina...")
                medicamento = request.form.get("nombre_medicamento")
                id_proveedor = request.form.get("ID_proveedor")
                nuevo_proveedor = request.form.get("nombre_proveedor")
                nuevo_proveedor_tel = request.form.get("telefono_proveedor")
                elegir_existente = request.form.get("elegir_proveedor")
                # endregion
                conn = mariadb.connect(**current_user.Conection)
                if conn is not None:
                    cursor = conn.cursor(dictionary=True)
                    try:
                        print(
                            f"{(medicamento, id_proveedor, nuevo_proveedor, nuevo_proveedor_tel, elegir_existente)}"
                        )
                        # region proveedor existente
                        if elegir_existente == "True":
                            verificar_proveedor = """
                                SELECT COUNT(*)
                                FROM proveedores
                                WHERE proveedores.ID_proveedor = ?
                                """
                            params = (id_proveedor,)
                            cursor.execute(verificar_proveedor, params)
                            count = cursor.fetchone()["COUNT(*)"]

                            print(f"{medicamento} | {id_proveedor} | SQL: {count}")
                            if count == 0:
                                raise Exception("No existe ese proveedor")
                            elif count == 1:
                                verificar_medicamento = """
                                    SELECT COUNT(*)
                                    FROM medicamento
                                    WHERE Nombre = ? AND ID_proveedor = ?
                                    """
                                params = (medicamento, id_proveedor)
                                cursor.execute(verificar_medicamento, params)
                                count = cursor.fetchone()["COUNT(*)"]
                                if count > 0:
                                    raise Exception("Registro de medicamento duplicado")

                                insertar_medicamento = """
                                    INSERT INTO medicamento
                                    (Nombre, ID_proveedor)
                                    VALUES
                                    (?, ?)
                                    """
                                params = (medicamento, id_proveedor)
                                cursor.execute(insertar_medicamento, params)
                                conn.commit()
                                print("Medicamento ingresado con éxito")
                        # endregion

                        # region proveedor nuevo
                        elif elegir_existente == "False":
                            app.logger.info("Ejecutando operación de agregar proveedor...")
                            verificar_proveedor = """
                                SELECT COUNT(*)
                                FROM proveedores
                                WHERE proveedores.Nombre = ? OR proveedores.`Teléfono` = ?
                                """
                            params = (nuevo_proveedor, nuevo_proveedor_tel)
                            cursor.execute(verificar_proveedor, params)
                            count = cursor.fetchone()["COUNT(*)"]

                            print(
                                f"{medicamento} | {nuevo_proveedor} | {nuevo_proveedor_tel} | SQL count: {count}"
                            )
                            if count > 0:
                                raise Exception("Proveedor duplicado")
                            else:
                                insertar_proveedor = """
                                    INSERT INTO proveedores
                                    (Nombre, Teléfono)
                                    VALUES
                                    (?, ?)
                                    """
                                params = (nuevo_proveedor, nuevo_proveedor_tel)
                                cursor.execute(insertar_proveedor, params)
                                app.logger.info(f"Operacion de agregar nuevo proveedor {nuevo_proveedor} completada correctamente")
                                insertar_medicamento = """
                                    INSERT INTO medicamento
                                    (Nombre, ID_proveedor)
                                    VALUES
                                    (?, LAST_INSERT_ID())
                                    """
                                params = (medicamento,)
                                cursor.execute(insertar_medicamento, params)
                                conn.commit()
                                print("Medicamento insertado con éxito")
                                app.logger.info(f"Operacion de agregar medicina {medicamento} completada correctamente")
                        # endregion
                        else:
                            raise Exception("Error formulario vulnerado!")
                    except Exception as e:
                        conn.rollback()
                        raise e
                    finally:
                        conn.close()
        except Exception as e:
            app.logger.error(f'Error en la operación de agregar medicina: {str(e)}')
            return jsonify({'message': f'Error en la operación de agregar medicina: {str(e)}'}), 500
    return redirect(url_for("Inventario"))


@app.route("/modificar_medicamento", methods=["POST"])
@login_required
@limiter.limit("10 per minute")
def modificar_medicamento():
    user_token = session['token']
    request_token = request.form.get('token_modificar')
    if request_token != user_token:
        app.logger.warning("Intento de acceso a la funcion de modificar medicina de usuario no autenticado.")
        return jsonify({'message': 'FORBIDDEN: NO AUTENTICADO'}), 403
    if lock_modificar_medicamento.locked():
        app.logger.warning("Intento de acceso a la funcion de modificar medicina mientras se encontraba en uso (blocked).")
        return jsonify({'message': 'BLOQUEADO: FUNCIÓN EN USO'}), 423
        
    try:
        with lock_modificar_medicamento:
            app.logger.info("Ejecutando operación de modificar medicina...")
            id_medicamento = request.form.get("modificar_medicina_id")
            nombre = request.form.get("modificar_medicina_nombre")
            telefono_proveedor = request.form.get("modificar_medicina_telefono")
            id_proveedor = request.form.get("modificar_medicina_id_proveedor")

            conn = mariadb.connect(**current_user.Conection)
            if conn is not None:
                try:
                    cursor = conn.cursor(dictionary=True)
                    verificar_medicamento = """
                        SELECT COUNT(*) 
                        FROM medicamento
                        WHERE ID_Medicamento = ?
                        """
                    params = (id_medicamento,)
                    cursor.execute(verificar_medicamento, params)
                    count = cursor.fetchone()["COUNT(*)"]
                    if count == 0:
                        raise Exception("Medicamento no encontrado")
                    update_medicamento = """
                        UPDATE medicamento 
                        SET Nombre = ?, ID_proveedor = ?
                        WHERE ID_Medicamento = ?
                        """
                    params = (nombre, id_proveedor, id_medicamento)
                    cursor.execute(update_medicamento, params)

                    update_proveedor = """
                        UPDATE proveedores
                        SET Teléfono = ?
                        WHERE ID_proveedor = ?
                        """
                    params = (telefono_proveedor, id_proveedor)
                    cursor.execute(update_proveedor, params)

                    conn.commit()
                    print("Medicamento actualizado")
                    app.logger.info(f"Operacion de modificar medicina {nombre} completada correctamente")
                except Exception as e:
                    conn.rollback()
                    raise e
                finally:
                    conn.close()
    except Exception as e:
        app.logger.error(f'Error en la operación de agregar medicina: {str(e)}')
        return jsonify({'message': f'Error en la operación de agregar medicina: {str(e)}'}), 500
    return redirect(url_for("Inventario"))


@app.route("/eliminar_medicamento", methods=["POST"])
@login_required
@limiter.limit("10 per minute")
def eliminar_medicamento():
    user_token = session['token']
    request_token = request.form.get('token_eliminar')
    if request_token != user_token:
        app.logger.warning("Intento de acceso a la funcion de eliminar medicina de usuario no autenticado.")
        return jsonify({'message': 'FORBIDDEN: NO AUTENTICADO'}), 403
    if lock_modificar_medicamento.locked():
        app.logger.warning("Intento de acceso a la funcion de eliminar medicina mientras se encontraba en uso (blocked).")
        return jsonify({'message': 'BLOQUEADO: FUNCIÓN EN USO'}), 423
        
    try:
        with lock_eliminar_medicamento:
            app.logger.info("Ejecutando operación de eliminar medicina...")
            id_medicamento = request.form.get("eliminar_medicamento_id")
            conn = mariadb.connect(**current_user.Conection)
            if conn is not None:
                try:
                    cursor = conn.cursor(dictionary=True)
                    verificar_medicamento = """
                        SELECT COUNT(*) 
                        FROM medicamento
                        WHERE ID_Medicamento = ?
                        """
                    params = (id_medicamento,)
                    cursor.execute(verificar_medicamento, params)
                    count = cursor.fetchone()["COUNT(*)"]
                    if count == 0:
                        raise Exception("Medicamento no encontrado")
                    delete_medicamento = """
                        DELETE FROM medicamento 
                        WHERE ID_Medicamento = ?
                        """
                    params = (id_medicamento,)
                    cursor.execute(delete_medicamento, params)
                    conn.commit()
                    print("Medicamento eliminado")
                    app.logger.info(f"Operacion de eliminar medicina con ID {id_medicamento} completada correctamente")
                except Exception as e:
                    conn.rollback()
                    raise e
                finally:
                    conn.close()
    except Exception as e:
        app.logger.error(f'Error en la operación de agregar medicina: {str(e)}')
        return jsonify({'message': f'Error en la operación de agregar medicina: {str(e)}'}), 500
    return redirect(url_for("Inventario"))


# endregion


@app.route("/Ajustes", methods=["GET"])
@login_required
def Ajustes():
    print(current_user.Conection)
    # Verificar si el usuario está autenticado
    if "Tipo_usuario" not in session:
        print("<No hay session>")
        return redirect(url_for("Índice"))

    return render_template("Ajustes.html", current_page="Ajustes")


@app.route("/Inicio", methods=["GET"])
@login_required
def Inicio():
    conn = mariadb.connect(**current_user.Conection)
    if conn:
        try:
            query = """
                SELECT datos_p.Nombres, datos_p.Apellido_Paterno, datos_p.Apellido_Materno,
                    Fecha, Motivo,
                    datos_d.Nombres AS Nombres_doctor, datos_d.Apellido_Paterno AS Apellido_p_doctor, datos_d.Apellido_Materno AS Apellido_m_doctor,
                    datos_r.Nombres AS Nombres_recep, datos_r.Apellido_Paterno AS Apellido_p_recep, datos_r.Apellido_Materno AS Apellido_m_recep
                FROM citas
                JOIN estatus_cita ON citas.ID_Estatus_Cita = estatus_cita.ID_Estatus_Cita
                #Paciente y sus datos
                JOIN pacientes ON citas.ID_Paciente = pacientes.ID_Paciente
                    JOIN datos_basicos AS datos_p ON pacientes.ID_Datos_Basicos = datos_p.ID_Datos_Basicos
                #Doctor y sus datos
                JOIN doctores ON citas.ID_Doctor = doctores.ID_Doctor
                    JOIN datos_basicos AS datos_d ON doctores.ID_Datos_Basicos = datos_d.ID_Datos_Basicos
                #Recepcionista y sus datos
                JOIN recepcionistas ON citas.ID_Recepcionista = recepcionistas.ID_Recepcionista
                    JOIN datos_basicos AS datos_r ON recepcionistas.ID_Datos_Basicos = datos_r.ID_Datos_Basicos
                """
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query)
            rows = cursor.fetchall()

            # print("Cita:")
            # print(utils.print_rows(rows))

            query_lista_pacientes = """
                SELECT ID_paciente, Nombres, Apellido_paterno, Apellido_materno FROM pacientes
                JOIN datos_basicos ON datos_basicos.ID_datos_basicos = pacientes.ID_datos_basicos
                """
            cursor.execute(query_lista_pacientes)
            lista_pacientes = cursor.fetchall()
            # print("Pacientes")
            # print(utils.print_rows(lista_pacientes))

            query_lista_doctores = """
                SELECT ID_doctor, Nombres, Apellido_paterno, Apellido_materno FROM doctores
                JOIN datos_basicos ON datos_basicos.ID_datos_basicos = doctores.ID_datos_basicos
                """
            cursor.execute(query_lista_doctores)
            lista_doctores = cursor.fetchall()
            print("Doctores")
            print(utils.print_rows(lista_doctores))
        except:
            pass
        finally:
            conn.close()
    return render_template(
        "Inicio.html",
        citas=rows,
        lista_pacientes=lista_pacientes,
        lista_doctores=lista_doctores,
        current_page="Inicio",
    )


# region Agregar y modificar cita
@app.route("/agregar_cita", methods=["POST"])
@login_required
@limiter.limit("10 per minute")
def agregar_cita():
    if request.method == "POST":
        user_token = session['token']
        request_token = request.form.get('token_agregar')
        if request_token != user_token:
            app.logger.warning("Intento de acceso a la funcion de agregar citas de usuario no autenticado.")
            return jsonify({'message': 'FORBIDDEN: NO AUTENTICADO'}), 403
        if lock_agregar_cita.locked():
            app.logger.warning("Intento de acceso a la funcion de agregar citas mientras se encontraba en uso (blocked).")
            return jsonify({'message': 'BLOQUEADO: FUNCIÓN EN USO'}), 423
        
        try:
            with lock_agregar_cita:
                app.logger.info("Ejecutando operación de agregar cita...")
                id_paciente = request.form.get("paciente")
                fecha = request.form.get("fecha")
                hora = request.form.get("hora")
                motivo = request.form.get("motivo")
                id_doctor = request.form.get("doctor")
                redirect_url = request.form.get("redirect")

                fechacita = datetime.strptime(f"{fecha} {hora}", "%Y-%m-%d %H:%M")
                print(
                    (
                        fechacita,
                        motivo,
                        id_paciente,
                        id_doctor,
                        1,
                        1,
                        1,
                    )
                )
                conn = mariadb.connect(**current_user.Conection)
                if conn:
                    insertar_cita = """
                        INSERT INTO citas 
                        (fecha, motivo, id_paciente, id_doctor, id_estatus_cita, id_recepcionista, id_receta)
                        VALUES (?,?,?,?,?,?,?)
                    """
                    params = (
                        fechacita,
                        motivo,
                        id_paciente,
                        id_doctor,
                        1,
                        1,
                        1,
                    )
                    cursor = conn.cursor(dictionary=True)
                    # Error
                    cursor.execute(insertar_cita, params)

                    cursor.execute("SELECT * FROM citas WHERE ID_cita = LAST_INSERT_ID()")
                    rows = cursor.fetchall()
                    utils.print_rows(rows)
                    conn.commit()
                    app.logger.info(f"Operacion de agregar cita con la fecha: {fechacita} completada correctamente")
        except Exception as e:
            app.logger.error(f'Error en la operación de agregar cita: {str(e)}')
            return jsonify({'message': f'Error en la operación de agregar cita: {str(e)}'}), 500
    return redirect(redirect_url)

# region modificar cita
@app.route("/modificar_cita", methods=["POST"])
@login_required
@limiter.limit("10 per minute")
def modificar_cita():
    if request.method == "POST":
        user_token = session['token']
        request_token = request.form.get('token_modificar')
        if request_token != user_token:
            app.logger.warning("Intento de acceso a la funcion de modificar citas de usuario no autenticado.")
            return jsonify({'message': 'FORBIDDEN: NO AUTENTICADO'}), 403
        if lock_modificar_cita.locked():
            app.logger.warning("Intento de acceso a la funcion de modificar citas mientras se encontraba en uso (blocked).")
            return jsonify({'message': 'BLOQUEADO: FUNCIÓN EN USO'}), 423
        
        try:
            with lock_modificar_cita:
                app.logger.info("Ejecutando operación de modificar cita...")
                print("/modificar_cita")
                id_cita = request.form.get("cita_mod")
                id_paciente = request.form.get("paciente_mod")
                id_doctor = request.form.get("doctor_mod")
                id_recepcionista = request.form.get("recepcionista_mod")
                motivo = request.form.get("motivo_mod")
                fecha = request.form.get("fecha_mod")
                hora = request.form.get("hora_mod")
                redirect_url = request.form.get("redirect")
                fechacita = datetime.strptime(f"{fecha} {hora}", "%Y-%m-%d %H:%M")
                print(
                    (
                        id_cita,
                        id_paciente,
                        motivo,
                        fecha,
                        hora,
                        fechacita,
                        redirect_url,
                        id_doctor,
                        id_recepcionista,
                    )
                )
                conn = mariadb.connect(**current_user.Conection)
                if conn is not None:
                    try:
                        cursor = conn.cursor(dictionary=True)
                        verificar_cita = """
                            SELECT COUNT(*) 
                            FROM citas
                            WHERE ID_Cita = ?
                            """
                        params = (id_cita,)
                        cursor.execute(verificar_cita, params)
                        count = cursor.fetchone()["COUNT(*)"]
                        if count == 0:
                            raise Exception("Cita no encontrada")
                        update_cita = """
                            UPDATE citas
                            SET fecha=?, motivo=?, id_paciente=?, id_doctor=?,  id_recepcionista=?
                            WHERE id_cita = ?
                            """
                        params = (
                            fechacita,
                            motivo,
                            id_paciente,
                            id_doctor,
                            id_recepcionista,
                            id_cita,
                        )
                        cursor.execute(update_cita, params)
                        conn.commit()
                        print("Cita actualizada")
                        app.logger.info(f"Operacion de modificar cita con la nueva fecha: {fechacita} completada correctamente")
                    except Exception as e:
                        conn.rollback()
                        raise e
                    finally:
                        conn.close()
        except Exception as e:
            app.logger.error(f'Error en la operación de modificar cita: {str(e)}')
            return jsonify({'message': f'Error en la operación de modificar cita: {str(e)}'}), 500
    return redirect(redirect_url)
# endregion

# region Eliminar cita
@app.route("/eliminar_cita", methods=["POST"])
@login_required
@limiter.limit("10 per minute")
def eliminar_cita():
    if request.method == "POST":
        user_token = session['token']
        request_token = request.form.get("token_eliminar")
        redirect_url = request.form.get("redirect")

    if request_token != user_token:
        app.logger.warning("Intento de acceso a la funcion de eliminar citas de usuario no autenticado.")
        return jsonify({'message': 'FORBIDDEN: NO AUTENTICADO'}), 403
    if lock_modificar_cita.locked():
        app.logger.warning("Intento de acceso a la funcion de eliminar citas mientras se encontraba en uso (blocked).")
        return jsonify({'message': 'BLOQUEADO: FUNCIÓN EN USO'}), 423
    try:
        with lock_modificar_cita:
            print("/eliminar_cita")
            app.logger.info("Ejecutando operación de eliminar cita...")
            id_cita = request.form.get("cita_id_eli")
            print(id_cita)
            conn = mariadb.connect(**current_user.Conection)
            if conn is not None:
                try:
                    cursor = conn.cursor(dictionary=True)
                    update_cita = """
                            UPDATE citas
                            SET ID_Estatus_Cita = 2
                            WHERE id_cita = ?
                            """
                    params = (id_cita,)
                    cursor.execute(update_cita, params)
                    conn.commit()
                    print("Cita actualizada")
                except Exception as e:
                    conn.rollback()
                    raise e
                finally:
                    conn.close()

    except Exception as e:
        app.logger.error(f'Error en la operación de eliminar cita: {str(e)}')
        return jsonify({'message': f'Error en la operación de eliminar cita: {str(e)}'}), 500
    return redirect(redirect_url)

@app.route("/Indice", methods=["GET"])
def Indice():
    # return f'{current_user}, {current_user.is_authenticated} , {current_user.is_anonymous} '
    return render_template("Índice.html", current_page='Indice')

# region APIs

@app.route("/api/citas/<year>/<month>", methods=["GET"])
@login_required
def citas_mes(year, month):
    conn = mariadb.connect(**current_user.Conection)
    if conn is not None:
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT citas.ID_cita, datos_p.Nombres, datos_p.Apellido_Paterno, datos_p.Apellido_Materno,
                Fecha, Motivo,
                datos_d.Nombres AS Doctor_Nombres, datos_d.Apellido_Paterno AS Doctor_Apellido_Paterno,
                datos_d.Apellido_Materno AS Doctor_Apellido_Materno,
                datos_r.Nombres AS Recepcionista_Nombres, datos_r.Apellido_Paterno AS Recepcionista_Apellido_Paterno, 
                datos_r.Apellido_Materno AS Recepcionista_Apellido_Materno
            FROM citas
            JOIN estatus_cita ON citas.ID_Estatus_Cita = estatus_cita.ID_Estatus_Cita
            #Paciente y sus datos
            JOIN pacientes ON citas.ID_Paciente = pacientes.ID_Paciente
            JOIN datos_basicos AS datos_p ON pacientes.ID_Datos_Basicos = datos_p.ID_Datos_Basicos
            #Doctor y sus datos
            JOIN doctores ON citas.ID_Doctor = doctores.ID_Doctor
            JOIN datos_basicos AS datos_d ON doctores.ID_Datos_Basicos = datos_d.ID_Datos_Basicos
            #Recepcionista y sus datos
            JOIN recepcionistas ON citas.ID_Recepcionista = recepcionistas.ID_Recepcionista
            JOIN datos_basicos AS datos_r ON recepcionistas.ID_Datos_Basicos = datos_r.ID_Datos_Basicos
            WHERE YEAR(Fecha) = ? AND MONTH(Fecha) = ?
        """
        params = (year, month)
        cursor.execute(query, params)
        citas = cursor.fetchall()
        utils.print_rows(citas)
        return jsonify(citas)
    return jsonify(None)


# Ruta para cargar las citas
@app.route("/api/citas/<year>/<month>/<day>", methods=["GET"])
@login_required
def post_test(year, month, day):
    conn = mariadb.connect(**current_user.Conection)
    if conn is not None:
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT citas.ID_cita, datos_p.Nombres, datos_p.Apellido_Paterno, datos_p.Apellido_Materno,
                Fecha, Motivo,
                pacientes.ID_Paciente, doctores.ID_Doctor, recepcionistas.ID_Recepcionista,
                datos_d.Nombres AS Doctor_Nombres, datos_d.Apellido_Paterno AS Doctor_Apellido_Paterno,
                datos_d.Apellido_Materno AS Doctor_Apellido_Materno,
                datos_r.Nombres AS Recepcionista_Nombres, datos_r.Apellido_Paterno AS Recepcionista_Apellido_Paterno, 
                datos_r.Apellido_Materno AS Recepcionista_Apellido_Materno
            FROM citas
            JOIN estatus_cita ON citas.ID_Estatus_Cita = estatus_cita.ID_Estatus_Cita
            #Paciente y sus datos
            JOIN pacientes ON citas.ID_Paciente = pacientes.ID_Paciente
            JOIN datos_basicos AS datos_p ON pacientes.ID_Datos_Basicos = datos_p.ID_Datos_Basicos
            #Doctor y sus datos
            JOIN doctores ON citas.ID_Doctor = doctores.ID_Doctor
            JOIN datos_basicos AS datos_d ON doctores.ID_Datos_Basicos = datos_d.ID_Datos_Basicos
            #Recepcionista y sus datos
            JOIN recepcionistas ON citas.ID_Recepcionista = recepcionistas.ID_Recepcionista
            JOIN datos_basicos AS datos_r ON recepcionistas.ID_Datos_Basicos = datos_r.ID_Datos_Basicos
            WHERE YEAR(Fecha) = ? AND MONTH(Fecha) = ? AND DAY(Fecha) = ? AND citas.ID_Estatus_Cita = 1;
        """
        params = (year, month, day)
        cursor.execute(query, params)
        citas = cursor.fetchall()
        utils.print_rows(citas)
        return jsonify(citas)
    return jsonify(None)


@app.route("/api/consulta/<tabla>", methods=["GET"])
@login_required
def consulta_tabla(tabla):
    print(f"{current_user.is_authenticated} {current_user.is_anonymous} {current_user}")
    if current_user.is_authenticated:
        print(current_user.get_id())
        print(current_user.Nombres)
        print(current_user.Apellido_Paterno)
        print(current_user.Apellido_Materno)
        print(current_user.ID_Datos_Basicos)
        print(current_user.Conection)

        conn = mariadb.connect(**current_user.Conection)
    if conn is not None:
        try:
            cursor = conn.cursor(dictionary = True)
            cursor.execute(f"SELECT * FROM {tabla}")
            results = cursor.fetchall()
            return jsonify(results)
        except:
            jsonify({"error": f"no hay tabla {tabla}"})
        finally:
            conn.close()
    return jsonify({"error": f"no hay conexión a la BD"})

@app.route("/api/consulta/privilegios", methods=["GET"])
@login_required
def consulta_privilegios():
    print(f"{current_user.is_authenticated} {current_user.is_anonymous} {current_user}")
    print(current_user.get_id())
    print(current_user.Conection)

    conn = mariadb.connect(**current_user.Conection)
    if conn is not None:
        try:
            cursor = conn.cursor()
            # cursor.execute(f"SELECT User, Host FROM mysql.user;")
            cursor.execute(f"SHOW GRANTS FOR 'Recepcionista'@'localhost'")
            results = cursor.fetchall()
            return jsonify(results)
        except:
            jsonify({"error": f"no se pueden ver los priviledios"})
        finally:
            conn.close()
    return jsonify({"error": f"no hay conexión a la BD"})

# endregion

app.run(host='0.0.0.0', port=5000)

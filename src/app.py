from flask import Flask, render_template, request, session, redirect, url_for, jsonify, abort, flash
import mariadb, utils, datetime
from config import ROOT_CONECTION
from models import Usuario
from flask_login import login_manager, LoginManager, current_user, login_user, logout_user, login_required

app = Flask(__name__)
app.config["DEBUG"] = True
app.secret_key = 'super secret key'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'Ingreso'

@login_manager.user_loader
def load_user(id:int):
    # Si ya inició sesión, se guarda el tipo de usuario y se recupera
    role_usuario = session.get('Tipo_usuario')
    if role_usuario is None:
        return None
    print(f'Rol de usuario actual: {role_usuario}')
    
    conn = mariadb.connect(**ROOT_CONECTION)
    if conn is not None:
        cursor = conn.cursor(dictionary=True)
        #region ternarios
        tabla = (
            'admin' if role_usuario == 'admin' else 
            'doctores' if role_usuario == 'doctor' else 
            'recepcionistas' if role_usuario == 'recepcionista' else 
            'none'
        )
        nombre_PK = (
            'ID_admin' if role_usuario == 'admin' else 
            'ID_doctor' if role_usuario == 'doctor' else 
            'ID_recepcionista' if role_usuario == 'recepcionista' else 
            'none'
        )
        query = f"""
            SELECT * FROM {tabla} 
            JOIN datos_basicos ON datos_basicos.ID_datos_basicos = {tabla}.ID_datos_basicos
            WHERE {nombre_PK}
        """
        #endregion
        cursor.execute(query)
        result = cursor.fetchone()
        if result is not None:
            utils.print_cols(result)
            usuario = Usuario(id=id, tipo_usuario=role_usuario, id_datos_basicos=result['ID_Datos_Basicos'], nombres=result['Nombres'], ap_pat=result['Apellido_Paterno'], ap_mat=result['Apellido_Materno'])
            return usuario
    return None

@app.errorhandler(401)
def error():
    return '<h1>ACCESO PROHIBIDO</h1>'


# Metodo para validar entradas
def validar_entrada(texto):
    # a-z y A-Z son para minusculas y mayusculas
    # \u00e1\u00e9\u00ed\u00f3\u00fa\u00f1\u00c1\u00c9\u00cd\u00d3\u00da\u00d1  Letras mayusculas y minusculas con acentos
    # \s Espacios en blanco
    # '' Al menos un caracter del conjunto
    # $ Al final de la cadena
    # Definimos el patrón que NO queremos en la entrada
    patron = r"^[a-zA-Z\u00e1\u00e9\u00ed\u00f3\u00fa\u00f1\u00c1\u00c9\u00cd\u00d3\u00da\u00d1\s]+$"

    # Buscamos si hay alguna coincidencia en el texto
    if not re.search(patron, texto):
        return False
    else:
        return True


# Metodo para poder realizar CUD> CREATE, UPDATE Y DELETE
def CUD(query, params=None):
    print("<-------------------- Conectando... --------------------")
    try:
        # Conectar a la BD
        connection = mariadb.connect(current_user.Conection)
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


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

# region login y registro
@app.route("/Registrarse", methods=["GET"])
def Registrarse():
    if current_user.is_authenticated:
        

        return redirect(url_for('Inicio'))

    return render_template("Registrarse.html")


@app.route("/Ingreso", methods=["GET"])
def Ingreso():
    print(current_user)
    print(current_user.is_authenticated)
    # Redireccionar
    if current_user.is_authenticated:
        flash('Ya haz iniciado sesión')
        print('Ya haz iniciado sesión')
        return redirect(url_for('Inicio'))
    
    #Solicitar datos  
    return render_template("Ingreso.html")

@app.route('/iniciar_sesion', methods=['POST'])
def logearse():
    if current_user.is_authenticated:
        print('FORBIDDEN')
        return redirect(url_for('Inicio'))

    tipo_sesion = request.form.get('elegir_sesion')
    if tipo_sesion == 'doctor':
        cedula = request.form.get('cedula-doctor')
        password = request.form.get('password')
        print(f'Iniciar sesion el doctor:\n{cedula}\n{password}')
        conn = mariadb.connect(**ROOT_CONECTION)
        if conn:
            try:
                usuario_existe = """
                    SELECT * FROM doctores
                    JOIN datos_basicos ON doctores.ID_datos_basicos = datos_basicos.ID_datos_basicos
                    WHERE Cedula_Profesional = ? AND Contraseña = ?
                    """
                params = (cedula, password,)

                cursor = conn.cursor(dictionary=True)
                cursor.execute(usuario_existe, params)
                result = cursor.fetchone()
                if result is not None:
                    # utils.print_cols(result)
                    # Aquí logeamos al usuario con flask-login
                    usuario = Usuario(id=result['ID_Doctor'], tipo_usuario=tipo_sesion, id_datos_basicos=result['ID_Datos_Basicos'], nombres=result['Nombres'], ap_pat=result['Apellido_Paterno'], ap_mat=result['Apellido_Materno'])
                    print(usuario)
                    login_user(usuario)
                    # También guardamos datos en la sesión
                    # session.clear()
                    session['Tipo_usuario'] = 'doctor'
                    session['ID_doctor'] = result['ID_Doctor']
                    session['ID_datos_basicos'] = result['ID_Datos_Basicos']
                    session['Nombres'] = result['Nombres']
                    session['Apellido_Paterno'] = result['Apellido_Paterno']
                    session['Apellido_Materno'] = result['Apellido_Materno']
            except:
                conn.rollback()
            finally:
                conn.close()
            pass
    elif tipo_sesion == 'recepcionista':
        rfc = request.form.get('rfc-recepcionista')
        password = request.form.get('password')
        conn = mariadb.connect(**ROOT_CONECTION)
        if conn:
            try:
                usuario_existe = """
                    SELECT * FROM recepcionistas
                    JOIN datos_basicos ON recepcionistas.ID_datos_basicos = datos_basicos.ID_datos_basicos
                    WHERE RFC = ? AND Contraseña = ?
                    """
                params = (rfc, password,)
                cursor = conn.cursor(dictionary=True)
                cursor.execute(usuario_existe, params)
                result = cursor.fetchone()
                if result is not None:
                    utils.print_cols(result)
                    # Aquí se logea la recepcionista
                    usuario = Usuario(id=result['ID_Recepcionista'], tipo_usuario=tipo_sesion, id_datos_basicos=result['ID_Datos_Basicos'], nombres=result['Nombres'], ap_pat=result['Apellido_Paterno'], ap_mat=result['Apellido_Materno'])
                    login_user(usuario)
                    # Se guardan datos en la session
                    # session.clear()
                    session['Tipo_usuario'] = 'recepcionista'
                    session['ID_recepcionista'] = result['ID_Recepcionista']
                    session['ID_datos_basicos'] = result['ID_Datos_Basicos']
                    session['Nombres'] = result['Nombres']
                    session['Apellido_Paterno'] = result['Apellido_Paterno']
                    session['Apellido_Materno'] = result['Apellido_Materno']
                    print(tipo_sesion)
            except:
                conn.rollback()
            finally:
                conn.close()
            pass

    else:
        print('error')

    return redirect(url_for('Inicio'))

@app.route('/logout', methods=['GET'])
@login_required
def logout():

    if "Tipo_usuario" not in session:
        print('FORBIDEN')
        return redirect(url_for('Inicio'))

    user = current_user
    if isinstance(user, Usuario):
        role = user.Tipo_usuario
        nombres = user.Nombres
        apellido_p = user.Apellido_Paterno
        print(f'Se cerró la sesión del {role} {nombres} {apellido_p} por el bien de la humanidad')
    logout_user()
    # session.clear()
    return redirect(url_for('Inicio'))
# endregion

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
        current_page='Agenda',
    )

# region pacientes
@app.route("/Pacientes", methods=["GET"])
@login_required
def Pacientes():
    query = "SELECT * FROM pacientes JOIN datos_basicos ON pacientes.ID_Datos_Basicos = datos_basicos.ID_Datos_Basicos"
    pacientes = Read(query)  # Llama a Read con la consulta adecuada
    return render_template("Pacientes.html", pacientes=pacientes, current_page='Pacientes')


@app.route("/Agregar_Pacientes", methods=["POST"])
@login_required
def agregar_Pacientes():
    # Solicita los datos del forms en Pacientes.html
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

    return redirect(url_for("Pacientes"))


@app.route("/Modificar_Pacientes", methods=["POST"])
@login_required
def modificar_Paciente():
    # Solicita los datos del forms en Pacientes.html
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
    return redirect(url_for("Pacientes"))


@app.route("/Eliminar_Pacientes", methods=["POST"])
@login_required
def eliminar_Paciente():
    # Solicita los datos del forms en Pacientes.html
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

@app.route('/agregar_medicamento', methods=['POST'])
@login_required
def agregar_medicamento():
    if request.method == 'POST':
        #region Form
        medicamento = request.form.get('nombre_medicamento')
        id_proveedor = request.form.get('ID_proveedor')
        nuevo_proveedor = request.form.get('nombre_proveedor')
        nuevo_proveedor_tel = request.form.get('telefono_proveedor')
        elegir_existente = request.form.get('elegir_proveedor')
        #endregion
        conn = mariadb.connect(**current_user.Conection)
        if conn is not None:
            cursor = conn.cursor(dictionary=True)
            try:
                print( f'{(medicamento, id_proveedor, nuevo_proveedor, nuevo_proveedor_tel, elegir_existente)}')
                #region proveedor existente
                if elegir_existente == 'True':
                    verificar_proveedor = """
                        SELECT COUNT(*)
                        FROM proveedores
                        WHERE proveedores.ID_proveedor = ?
                        """
                    params = (id_proveedor,)
                    cursor.execute(verificar_proveedor, params)
                    count = cursor.fetchone()['COUNT(*)']

                    print(f'{medicamento} | {id_proveedor} | SQL: {count}')
                    if count == 0:
                        raise Exception('No existe ese proveedor')
                    elif count == 1:
                        verificar_medicamento = """
                            SELECT COUNT(*)
                            FROM medicamento
                            WHERE Nombre = ? AND ID_proveedor = ?
                            """
                        params = (medicamento, id_proveedor)
                        cursor.execute(verificar_medicamento, params)
                        count = cursor.fetchone()['COUNT(*)']
                        if count > 0:
                            raise Exception('Registro de medicamento duplicado')
                        
                        insertar_medicamento = """
                            INSERT INTO medicamento
                            (Nombre, ID_proveedor)
                            VALUES
                            (?, ?)
                            """
                        params = (medicamento, id_proveedor)
                        cursor.execute(insertar_medicamento, params)
                        conn.commit()
                        print('Medicamento ingresado con éxito')
                #endregion

                #region proveedor nuevo
                elif elegir_existente == 'False':
                    verificar_proveedor = """
                        SELECT COUNT(*)
                        FROM proveedores
                        WHERE proveedores.Nombre = ? OR proveedores.`Teléfono` = ?
                        """
                    params = (nuevo_proveedor, nuevo_proveedor_tel)
                    cursor.execute(verificar_proveedor, params)
                    count = cursor.fetchone()['COUNT(*)']

                    print(f'{medicamento} | {nuevo_proveedor} | {nuevo_proveedor_tel} | SQL count: {count}')
                    if count > 0:
                        raise Exception('Proveedor duplicado')
                    else:
                        insertar_proveedor = """
                            INSERT INTO proveedores
                            (Nombre, Teléfono)
                            VALUES
                            (?, ?)
                            """
                        params = (nuevo_proveedor, nuevo_proveedor_tel)
                        cursor.execute(insertar_proveedor, params)
                        
                        insertar_medicamento = """
                            INSERT INTO medicamento
                            (Nombre, ID_proveedor)
                            VALUES
                            (?, LAST_INSERT_ID())
                            """
                        params = (medicamento,)
                        cursor.execute(insertar_medicamento, params)
                        conn.commit()
                        print('Medicamento insertado con éxito')
                #endregion
                else:
                    raise Exception('Error formulario vulnerado!')
            except Exception as e:
                conn.rollback()
                raise e
            finally:
                conn.close()

    return redirect(url_for('Inventario'))

@app.route('/modificar_medicamento', methods=['POST'])
@login_required
def modificar_medicamento():
    id_medicamento = request.form.get('modificar_medicina_id')
    nombre = request.form.get('modificar_medicina_nombre')
    telefono_proveedor = request.form.get('modificar_medicina_telefono')
    id_proveedor = request.form.get('modificar_medicina_id_proveedor')

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
            count = cursor.fetchone()['COUNT(*)']
            if count == 0:
                raise Exception('Medicamento no encontrado')
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
            print('Medicamento actualizado')
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    return redirect(url_for('Inventario'))

@app.route('/eliminar_medicamento', methods=['POST'])
@login_required
def eliminar_medicamento():
    id_medicamento = request.form.get('eliminar_medicamento_id')
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
            count = cursor.fetchone()['COUNT(*)']
            if count == 0:
                raise Exception('Medicamento no encontrado')
            delete_medicamento = """
                DELETE FROM medicamento 
                WHERE ID_Medicamento = ?
                """
            params = (id_medicamento,)
            cursor.execute(delete_medicamento, params)
            conn.commit()
            print('Medicamento actualizado')
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    return redirect(url_for('Inventario'))
# endregion

@app.route("/Ajustes", methods=["GET"])
@login_required
def Ajustes():
    print(current_user.Conection)
    # Verificar si el usuario está autenticado
    if "Tipo_usuario" not in session:
        print("<No hay session>")
        return redirect(url_for("Índice"))
    
    return render_template("Ajustes.html", current_page='Ajustes')


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
        current_page='Inicio'
    )

# region Agregar y modificar cita
@app.route("/agregar_cita", methods=["POST"])
@login_required
def agregar_cita():
    if request.method == "POST":
        id_paciente = request.form.get("paciente")
        fecha = request.form.get("fecha")
        hora = request.form.get("hora")
        motivo = request.form.get("motivo")
        id_doctor = request.form.get("doctor")
        redirect_url = request.form.get("redirect")

        fechacita = datetime.datetime.strptime(f"{fecha} {hora}", "%Y-%m-%d %H:%M")
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
    return redirect(redirect_url)

@app.route("/modificar_cita", methods=["POST"])
@login_required
def modificar_cita():
    print("/modificar_cita")
    if request.method == "POST":
        id_cita = request.form.get("cita_mod")
        id_paciente = request.form.get("paciente_mod")
        id_doctor = request.form.get("doctor_mod")
        id_recepcionista = request.form.get("recepcionista_mod")
        motivo = request.form.get("motivo_mod")
        fecha = request.form.get("fecha_mod")
        hora = request.form.get("hora_mod")
        redirect_url = request.form.get("redirect")
        fechacita = datetime.datetime.strptime(f"{fecha} {hora}", "%Y-%m-%d %H:%M")
        print(
            (
                id_cita,
                id_paciente,
                motivo,
                fechacita,
                redirect_url,
                id_doctor,
                id_recepcionista,
            )
        )
    return redirect(redirect_url)
# endregion

@app.route("/Indice", methods=["GET"])
def Indice():
    # return f'{current_user}, {current_user.is_authenticated} , {current_user.is_anonymous} '
    return render_template("Índice.html")


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
            WHERE YEAR(Fecha) = ? AND MONTH(Fecha) = ? AND DAY(Fecha) = ?
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
    print(f'{current_user.is_authenticated} {current_user.is_anonymous} {current_user}')
    print(current_user.get_id())
    print(current_user.Nombres)
    print(current_user.Apellido_Paterno)
    print(current_user.Apellido_Materno)
    print(current_user.ID_Datos_Basicos)
    print(current_user.Conection)

    conn = mariadb.connect(**current_user.Conection)
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute(f'SELECT * FROM {tabla}')
            results = cursor.fetchall()
            return jsonify(results)
        except:
            jsonify({ 'error': f'no hay tabla {tabla}' })
        finally:
            conn.close()
    return jsonify({ 'error': f'no hay conexión a la BD' })

@app.route("/api/consulta/privilegios", methods=["GET"])
@login_required
def consulta_privilegios():
    print(f'{current_user.is_authenticated} {current_user.is_anonymous} {current_user}')
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
            jsonify({ 'error': f'no se pueden ver los priviledios'})
        finally:
            conn.close()
    return jsonify({ 'error': f'no hay conexión a la BD' })

app.run()

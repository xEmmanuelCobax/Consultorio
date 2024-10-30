let selectedRow = null;

let timerID = {
    agregar: null,
    modificar: null,
    eliminar: null
}
let modalTimeout = {
    agregar: null,
    modificar: null,
    eliminar: null
}
const socket = io();

document.querySelectorAll('.clickable-row').forEach(row => {
    row.addEventListener('click', function () {
        if (view == 'Pacientes') {
            // Seleccionar fila
            if (selectedRow) {
                selectedRow.classList.remove('table-primary');
            }
            selectedRow = this;
            selectedRow.classList.add('table-primary');
            // Guardar en las variables
            const id = row.getAttribute('data-id');
            const nombre = row.children[0].textContent;
            const apellidoP = row.children[1].textContent.split(' ')[0]; // Obtener primer apellido
            const apellidoM = row.children[1].textContent.split(' ')[1]; // Obtener segundo apellido
            const telefono = row.children[2].textContent;
            const email = row.children[3].textContent;
            const fechaNacimiento = row.children[4].textContent;
            const direccion = row.children[5].textContent;
            // Verificar los datos con la consola 
            console.log(id)
            console.log(nombre)
            console.log(apellidoP)
            console.log(apellidoM)
            console.log(telefono)
            console.log(email)
            console.log(fechaNacimiento)
            console.log(direccion)
            // Asignar valores al modal
            document.getElementById('paciente_id').value = id;
            document.getElementById('paciente_id_eli').value = id;
            document.getElementById('nombre_paciente_mod').value = nombre;
            document.getElementById('apellido_p_paciente_mod').value = apellidoP;
            document.getElementById('apellido_m_paciente_mod').value = apellidoM;
            document.getElementById('telefono_paciente_mod').value = telefono;
            document.getElementById('email_paciente_mod').value = email;
            document.getElementById('fecha_n_paciente_mod').value = fechaNacimiento;
            document.getElementById('direccion_paciente_mod').value = direccion;
        }
        if (view == 'Inventario') {
            // Seleccionar fila
            if (selectedRow) {
                selectedRow.classList.remove('table-primary');
            }
            selectedRow = this;
            selectedRow.classList.add('table-primary');

            const id = row.getAttribute('id'); // ID
            const nombre = row.children[0].textContent; // Ajustado a [0] para "Nombre"
            const proveedor = row.children[1].textContent; // Ajustado a [1] para "Dosis"
            const telefono = row.children[2].textContent; // Ajustado a [1] para "Dosis"
            const id_proveedor = row.children[2].getAttribute('id');

            // Verificar los datos con la consola 
            console.log(id)
            console.log(nombre)
            console.log(proveedor)
            console.log(telefono)
            console.log(id_proveedor)

            // Asignar valores al modal
            document.getElementById('modificar_medicina_id').value = id;
            document.getElementById('modificar_medicina_nombre').value = nombre;
            document.getElementById('modificar_medicina_telefono').value = telefono;
            document.getElementById('modificar_medicina_id_proveedor').value = id_proveedor;

            //Asignar para eliminar
            document.getElementById('eliminar_medicamento_id').value = id;
            console.log(document.getElementById('eliminar_medicamento_id').value)
        }
    });
});

// Solicitar el estado de los botones al cargar la vista
socket.emit('request_button_states', { view });

// Actualizar los botones según el estado recibido
socket.on(`update_${view}_states`, function (states) {
    ['agregar', 'modificar', 'eliminar'].forEach(action => {
        const button = document.getElementById(`${action}${view}Boton`);
        if (button) {
            button.disabled = states[action];
            button.textContent = states[action]
                ? `${action.charAt(0).toUpperCase() + action.slice(1)} (En uso por otro usuario)`
                : action.charAt(0).toUpperCase() + action.slice(1);
        }
    });
});


// Evento Flask-IO para actualizar el estado de los botones
// Un método de flask llama a socket.emit('lock')
socket.on('lock', function (data) {
    const { view, action, status } = data;
    const buttonMap = {
        Pacientes: {
            agregar: 'agregarPacientesBoton',
            modificar: 'modificarPacientesBoton',
            eliminar: 'eliminarPacientesBoton'
        },
        Citas: {
            agregar: 'agregarCitasBoton',
            modificar: 'modificarCitasBoton',
            eliminar: 'eliminarCitasBoton'
        },
        Inventario: {
            agregar: 'agregarInventarioBoton',
            modificar: 'modificarInventarioBoton',
            eliminar: 'eliminarInventarioBoton'
        }
    };

    if (buttonMap[view][action]) {
        const button = document.getElementById(buttonMap[view][action]);
        button.disabled = status;
        if (status) {
            button.textContent = `${action.charAt(0).toUpperCase() + action.slice(1)} (En uso por otro usuario)`;
        } else {
            button.textContent = action.charAt(0).toUpperCase() + action.slice(1);
        }
    }
});

// Función para manejar el timeout
function handleModalTimeout(view, action, modal) {
    const span = document.getElementById(`segundosModal${action}`);
    let tiempoRestante = 180; // Inicializa el tiempo restante
    span.textContent = `Segundos restantes de solicitud: 180`; // Reiniciar el texto a 60

    if (modalTimeout[action]) {
        clearTimeout(modalTimeout[action]);
    }
    if (timerID[action]) {
        clearInterval(timerID[action]);
    }

    modalTimeout[action] = setTimeout(() => {
        socket.emit('unlock_button', { view }, { action }); // Desbloquear el botón
        modal.hide(); // Cerrar el modal
    }, 180000); // 180 segundos

    timerID[action] = setInterval(() => {
        if (tiempoRestante > 0) {
            tiempoRestante--;
            span.textContent = `Segundos restantes de solicitud: ${tiempoRestante}`;
        } else {
            clearInterval(timerID[action]);
        }
    }, 1000);
}

function unlockAgregarButton(view) {
    clearTimeout(modalTimeout.agregar);
    socket.emit('unlock_button', { view, action: 'agregar' });
    console.log(`Desbloqueado agregar`)
}

function unlockModificarButton(view) {
    clearTimeout(modalTimeout.modificar);
    socket.emit('unlock_button', { view, action: 'modificar' });
    console.log(`Desbloqueado modif`);
}

function unlockEliminarButton(view) {
    clearTimeout(modalTimeout.eliminar);
    socket.emit('unlock_button', { view, action: 'eliminar' });
    console.log(`Desbloqueado elim`)
}

// Evento para el botón Agregar
document.getElementById(`agregar${view}Boton`).addEventListener('click', function () {
    const modal = new bootstrap.Modal(document.getElementById(`modalAgregar${view}`));
    socket.emit('lock_button', { view, action: 'agregar' }); // Emitir evento para intentar bloquear
    modal.show();
    handleModalTimeout(view, 'agregar', modal); // Manejar el timeout
    document.getElementById(`modalAgregar${view}`).addEventListener('hidden.bs.modal', function () { unlockAgregarButton(view) });
    document.getElementById(`modalAgregar${view}`).addEventListener('submit', function () { unlockAgregarButton(view) });
});

// Evento para el botón Modificar
document.getElementById(`modificar${view}Boton`).addEventListener('click', function () {
    if (!selectedRow) {
        alert('Por favor selecciona una fila para modificar.');
        return;
    }
    const modal = new bootstrap.Modal(document.getElementById(`modalModificar${view}`));
    socket.emit('lock_button', { view, action: 'modificar' }); // Emitir evento para intentar bloquear
    modal.show();
    handleModalTimeout(view, 'modificar', modal); // Manejar el timeout
    document.getElementById(`modalModificar${view}`).addEventListener('hidden.bs.modal', function () { unlockModificarButton(view) });
    document.getElementById(`modalModificar${view}`).addEventListener('submit', function () { unlockModificarButton(view) });
});

// Evento para el botón Eliminar
document.getElementById(`eliminar${view}Boton`).addEventListener('click', function () {
    if (!selectedRow) {
        alert('Por favor selecciona una fila para eliminar.');
        return;
    }
    const modal = new bootstrap.Modal(document.getElementById(`modalEliminar${view}`));
    socket.emit('lock_button', { view, action: 'eliminar' }); // Emitir evento para intentar bloquear
    modal.show();
    handleModalTimeout(view, 'eliminar', modal); // Manejar el timeout
    document.getElementById(`modalEliminar${view}`).addEventListener('hidden.bs.modal', function () { unlockEliminarButton(view) })
    document.getElementById('eliminate').addEventListener('click', function () { unlockEliminarButton(view) })
    document.getElementById('cancel').addEventListener('click', function () { unlockEliminarButton(view) })
});
// aquí voy a importar funciones para validar formularios   
/*
Documentación:
Poner en el form: submit-validation
Poner en el input: needs-validation [OPCIÓN]

OPCIONES:
numeric 
alpha
alphanumeric 
alpha-hyphen
name

NO USAR LAS VALIDACIONES CONSTANTES, ESAS SE APLICAN AUTOMÁTICAMENTE
*/
function simpleValidation(element) {
    if (element.style.display === 'none' || element.parentElement.style.display === 'none') 
        return
    if (element.checkValidity()) {
        element.classList.add('is-valid')
        element.classList.remove('is-invalid')
    } else {
        element.classList.remove('is-valid')
        element.classList.add('is-invalid')
    }
}

// mapear inputValidations
const inputValidations = {
    'numeric': (e) => {
        if (e.value === '') return
        if (e.value.match(/^[0-9]{10}/)) {
            e.classList.add('is-valid')
            e.classList.remove('is-invalid')
        } else {
            e.classList.remove('is-valid')
            e.classList.add('is-invalid')
        }
    },
    'alpha': (e) => {
        if (e.value === '') return
        simpleValidation(e)
    },
    'alpha-hyphen': (e) => {
        if (e.value === '') return
        if (e.value.match(/^([a-zA-ZÀ-ú]{1,})([\-]?[a-zA-ZÀ-ú]{1,})*$/)) {
            e.classList.add('is-valid')
            e.classList.remove('is-invalid')
        } else {
            e.classList.remove('is-valid')
            e.classList.add('is-invalid')
        }
    },
    'alphanumeric': (e) => {
        if (e.value === '') return
        if (e.value.match(/^[a-zA-Z0-9]+(-[a-zA-Z0-9]+)*$/)) {
            e.classList.add('is-valid')
            e.classList.remove('is-invalid')
        } else {
            e.classList.remove('is-valid')
            e.classList.add('is-invalid')
        }
    },
    'simple': (e) => {
        if (e.value === '') return
        
        simpleValidation(e)
    },
    'mayus': (e) => {
        if (e.value === '') return

        e.value = e.value.toUpperCase();
    },
    'trim': (e) => {
        if (e.value === '') return
        e.value = e.value.replace(/[^A-Za-záéíóúÁÉÍÓÚñÑ\s]/g, '')
    }
}

const unfocusValidations = {
    'name': (e) => {
        if (e.value === '') return
        
        let split = e.value.split(' ')
        let result = ''
        for (var i = 0; i < split.length; i++) {
            let palabra = split[i].toLowerCase()
            if (palabra == null || palabra.length == 0) {
                continue
            }
            palabra = palabra[0].toUpperCase() + palabra.slice(1)
            result = result.concat(` ${palabra}`)
        }
        e.value = result
            .replace(' De ', ' de ').replace(' La ', ' la ')
            .replace(' Del ', ' del ').replace(' Las ', ' las ')
            .replace(/\-[a-z]/g, char => char.toUpperCase())
    }
}

const constValidations = {
    'trim': (e) => {
        if (e.value === '') return
        e.value = e.value.trim()
    },
    'empty': (e) => {
        if (e.value === '') {
            console.log(`Input vacío: ${e.name}`)
            e.classList.remove('is-valid')
            e.classList.remove('is-invalid')
        }
    },
    'min-length': (e) => {
        if (e.value === '') return
        let minLengthValue = e.getAttribute('minlength')
        if (minLengthValue === null) return

        let notAllowed = (minLengthValue !== null && e.value.length < minLengthValue)
        if (!e.checkValidity() || notAllowed) {
            console.log(`Input no válido: ${e.name}`)
            e.classList.remove('is-valid')
            e.classList.add('is-invalid')
        } else {
            console.log(`Input validado: ${e.name}`)
            e.classList.add('is-valid')
            e.classList.remove('is-invalid')
        }
    },
    'pattern': (e) => {
        if (e.value === '') return
        if (!e.hasAttribute('pattern')) return
        
        const pattern = e.getAttribute("pattern")
        const regex = new RegExp(`^${pattern}$`);
        if (regex.test(e.value)) {
            e.classList.add('is-valid')
            e.classList.remove('is-invalid')
        } else {
            e.classList.remove('is-valid')
            e.classList.add('is-invalid')
        }
    }
}

const elementsToValidate = document.getElementsByClassName('needs-validation')
const array = Array.from(elementsToValidate)
array.forEach(element => {
    if (element.classList.contains('numeric')) {
        element.onkeydown = (evt) => {
            if (evt.keyCode == 37 || evt.keyCode == 38 || evt.keyCode == 39 || evt.keyCode == 40 || evt.keyCode == 13 || evt.keyCode == 27 || evt.keyCode == 8 || evt.keyCode == 9)
                return true
            if (`${evt.key}`.match(/[0-9]/)){
                if (!evt.target.checkValidity()) {
                    evt.target.classList.remove('is-valid')
                    evt.target.classList.add('is-invalid')
                } else {
                    evt.target.classList.add('is-valid')
                    evt.target.classList.remove('is-invalid')
                }
                return true;
            }
            return false;
        }
        element.setAttribute('pattern', "^[0-9]{10}$")
    }
    if (element.classList.contains('alpha')) {
        element.setAttribute('pattern', "^([a-zA-ZÀ-ú]{2,})*$")
    }
    if (element.classList.contains('alphanumeric')) {
        element.setAttribute('pattern', "^[a-zA-ZÀ-ú0-9]+(-[a-zA-Z0-9]+)*$")
    }
    if (element.classList.contains('name')) {
        element.setAttribute('pattern', "^([a-zA-ZÀ-ú]{2,})([ \\-]?[a-zA-ZÀ-ú]{2,})*$")
    }

    const handleValidation = (evt) => {
        console.log('input')
        for (const validation in inputValidations) {
            if (element.classList.contains(validation)){
                inputValidations[validation](element)
            }
        }
        constValidations['pattern'](element)
        constValidations['min-length'](element)
        constValidations['empty'](element)
    }

    element.addEventListener('input', handleValidation)
    element.addEventListener('paste', handleValidation)
    element.addEventListener('change', handleValidation)

    element.addEventListener('blur', (evt) => {
        console.log('blur')
        for (const validation in inputValidations) {
            if (element.classList.contains(validation)){
                inputValidations[validation](element)
            }
        }
        for (const validation in unfocusValidations) {
            if (element.classList.contains(validation)){
                unfocusValidations[validation](element)
            }
        }
        setTimeout(() => {
            constValidations['min-length'](element)
            constValidations['trim'](element)
            constValidations['empty'](element)
        }, 10);
    })
});

const focusElements = document.getElementsByClassName('onfocus')
const focusArray = Array.from(focusElements)
focusArray.forEach(input => {
    console.log('focus')
    if (input.value === '') 
        return;
    simpleValidation()
})

const forms = document.getElementsByClassName('submit-validation')
const formsArray = Array.from(forms)
formsArray.forEach(form => {
    form.addEventListener('submit', evt => {
        evt.preventDefault()
        evt.stopPropagation()
        // Delay
        setTimeout(() => {
            if (!form.checkValidity()) {
                evt.preventDefault()
                evt.stopPropagation()
    
                Array.from(form.getElementsByTagName('input')).forEach(input => {
                    // radio check submit
                    if (input.type === 'radio' || input.type === 'submit' || input.type === 'check')
                        return
                    simpleValidation(input)
                })
            } else form.submit()
        }, 100);
    })
})

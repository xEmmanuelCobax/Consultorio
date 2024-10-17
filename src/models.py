from flask_login import UserMixin
from config import ROOT_CONECTION, DOCTOR_CONECTION, RECEPCIONIST_CONECTION

class Usuario(UserMixin):
    def __init__(self, id : int, tipo_usuario : str, id_datos_basicos = 0, nombres = '', ap_pat='', ap_mat = '') -> None:
        super().__init__()
        self.id = id
        self._tipo_usuario = tipo_usuario
        self._id_datos_basicos = id_datos_basicos
        self._nombres = nombres
        self._apellido_paterno = ap_pat
        self._apellido_materno = ap_mat

        if tipo_usuario.lower() == 'admin':
            self._conection = ROOT_CONECTION
        elif tipo_usuario.lower() == 'doctor':
            self._conection = DOCTOR_CONECTION
        elif tipo_usuario.lower() == 'recepcionista':
            self._conection = RECEPCIONIST_CONECTION
        else:
            self._conection = None
    
    @property
    def Nombres(self):
        return self._nombres
    
    @property
    def Tipo_usuario(self):
        return self._tipo_usuario
    
    @property
    def ID_Datos_Basicos(self):
        return self._id_datos_basicos
         
    @property
    def Apellido_Paterno(self):
        return self._apellido_paterno
         
    @property
    def Apellido_Materno(self):
        return self._apellido_materno

    @property
    def Conection(self):
        return self._conection


    def __str__(self) -> str:
        return f'Usuario: ID={self.id} Rol: {self._tipo_usuario}'
    
    def to_dict(self):
        return {
            'ID': self.id,
            'Tipo de usuario': self.tipo_usuario
        }


"""
  current_user.get_id()
  current_user.Nombres
  current_user.Apellido_Materno
  current_user.Apellido_Paterno
  current_user.ID_Datos_Basicos
"""
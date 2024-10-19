        # conn = mariadb.connect(**current_user.Conection)
        # if conn is not None:
        #     try:
        #         cursor = conn.cursor(dictionary=True)
        #         verificar_cita = """
        #             SELECT COUNT(*) 
        #             FROM medicamento
        #             WHERE ID_Cita = ?
        #             """
        #         params = (id_cita,)
        #         cursor.execute(verificar_cita, params)
        #         count = cursor.fetchone()['COUNT(*)']
        #         if count == 0:
        #             raise Exception('Cita no encontrada')
        #         update_cita = """
        #             UPDATE cita
        #             SET fecha=?, motivo=?, id_paciente=?, id_doctor=?, id_estatus_cita=?, id_recepcionista=?, id_receta=?
        #             WHERE id_cita = ?
        #             """
        #         params = (fecha, motivo, id_paciente, id_doctor, id_estatus_cita, id_recepcionista, id_receta, id_cita)
        #         cursor.execute(update_cita, params)
        #         conn.commit()
        #         print('Cita actualizada')
        #     except Exception as e:
        #         conn.rollback()
        #         raise e
        #     finally:
        #         conn.close()
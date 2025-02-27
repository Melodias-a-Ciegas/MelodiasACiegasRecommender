# recommendation.py
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session
from models import CancionInfo, Intento
from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy import func

def get_recommendations(user_id: int, db: Session, alpha: float = 0.1, default_difficulty: float = 3.0, top_n: int = 5):
    # 1. Cargar datos de Cancion_Info desde la base de datos
    canciones = db.query(CancionInfo).all()
    if not canciones:
        return []

    # Convertir objetos SQLAlchemy a lista de diccionarios
    data = []
    for c in canciones:
        data.append({
            "idCancionId": c.idCancionId,
            "nombre": c.nombre,
            "numero_total_notas": c.numero_total_notas,
            "densidad_notas": c.densidad_notas,
            "cantidad_saltos_grandes": c.cantidad_saltos_grandes,
            "notas_mano_izquierda": c.notas_mano_izquierda,
            "notas_mano_derecha": c.notas_mano_derecha,
            "tuplets": c.tuplets,
            "compositor": c.compositor
        })
    df_cancion = pd.DataFrame(data)

    # 2. Consultar los intentos del usuario que fueron satisfactorios
    # Se usa porcentaje_completado == 1 y se filtra para calificaciones entre 1 y 5
    df_intentos = pd.read_sql(
        db.query(Intento).filter(
            Intento.id_usuario == user_id,
            Intento.porcentaje_completado == 1,
            Intento.id_calificacion < 6  # se excluyen los "no calificados"
        ).statement,
        db.bind
    )

    print("Intentos del usuario: ", df_intentos)
    
    # Extraer los id_cancion que el usuario ya tocó satisfactoriamente
    canciones_usuario = df_intentos["id_cancion"].unique() if not df_intentos.empty else np.array([])
    # Generar target de dificultad a partir de las calificaciones del usuario (si existen)
    diff_target = None
    if not df_intentos.empty:
        diff_target = df_intentos["id_calificacion"].mean()  # este valor es de tipo float
    # 3. Definir las columnas de características numéricas
    cols_features = [
        "numero_total_notas", 
        "densidad_notas", 
        "cantidad_saltos_grandes", 
        "notas_mano_izquierda", 
        "notas_mano_derecha", 
        "tuplets"
    ]
    
    # Verificar que existan estas columnas en el DataFrame
    for col in cols_features:
        if col not in df_cancion.columns:
            raise ValueError(f"La columna {col} no se encuentra en Cancion_Info.")

    # 4. Consultar la dificultad promedio de cada canción a partir de los intentos de todos los usuarios.
    # Se calcula la media de id_calificacion para cada id_cancion (filtrando solo valores de 1 a 5)
    dificultad_data = db.query(
        Intento.id_cancion,
        func.avg(Intento.id_calificacion).label("avg_dificultad")
    ).filter(Intento.id_calificacion < 6).group_by(Intento.id_cancion).all()
    
    # Convertir a diccionario y forzar a float los valores de dificultad
    diff_by_song = {row.id_cancion: float(row.avg_dificultad) for row in dificultad_data}

    # Agregar la “dificultad” para cada canción en el DataFrame; si no tiene datos, se asigna default_difficulty
    df_cancion["dificultad"] = df_cancion["idCancionId"].apply(lambda x: float(diff_by_song.get(x, default_difficulty)))
    
    # 5. Escalar las características de las canciones
    scaler = StandardScaler()
    X = df_cancion[cols_features].values
    X_scaled = scaler.fit_transform(X)
    
    # Agregar los valores escalados a un DataFrame auxiliar
    df_cancion_scaled = df_cancion.copy()
    for idx, col in enumerate(cols_features):
        df_cancion_scaled[col] = X_scaled[:, idx]
    
    # 6. Construir el perfil del usuario según las canciones tocadas exitosamente
    user_profile = None
    if len(canciones_usuario) > 0:
        df_usuario = df_cancion_scaled[df_cancion_scaled["idCancionId"].isin(canciones_usuario)]
        if not df_usuario.empty:
            user_profile = df_usuario[cols_features].mean().values.reshape(1, -1)

    # 7. Generar las recomendaciones
    if user_profile is not None:
        # Calcular similitud coseno entre el perfil del usuario y todas las canciones
        sim_scores = cosine_similarity(user_profile, df_cancion_scaled[cols_features].values)
        df_cancion_scaled["similitud"] = sim_scores.flatten()
    
        # Excluir las canciones que el usuario ya tocó
        df_recomendar = df_cancion_scaled[~df_cancion_scaled["idCancionId"].isin(canciones_usuario)].copy()
    
        # Ordenar según similitud base
        df_recomendar = df_recomendar.sort_values(by="similitud", ascending=False)
    
        # Ajustar por dificultad si se obtuvo diff_target
        if diff_target is not None:
            # Convertir a float la columna dificultad para evitar operaciones con Decimal
            df_recomendar["dificultad"] = df_recomendar["dificultad"].astype(float)
            df_recomendar["diff_score"] = abs(df_recomendar["dificultad"] - diff_target)
            df_recomendar["score_final"] = df_recomendar["similitud"] - alpha * df_recomendar["diff_score"]
            df_recomendar = df_recomendar.sort_values(by="score_final", ascending=False)
        else:
            df_recomendar["score_final"] = df_recomendar["similitud"]
    
        recomendaciones = df_recomendar.head(top_n)
    else:
        # Cold start: ranking global basado en dificultad intermedia (default_difficulty)
        df_cancion_scaled["dificultad"] = df_cancion_scaled["dificultad"].astype(float)
        df_cancion_scaled["puntaje_default"] = -abs(df_cancion_scaled["dificultad"] - default_difficulty)
        recomendaciones = df_cancion_scaled.sort_values(by="puntaje_default", ascending=False).head(top_n)
        recomendaciones["score_final"] = recomendaciones["puntaje_default"]
    
    # Seleccionar las columnas a retornar
    cols_result = ["idCancionId", "nombre", "compositor", "dificultad", "score_final"]
    result = recomendaciones[cols_result].to_dict(orient="records")
    
    return result

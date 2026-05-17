from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


POWERBI_SEGMENT_LABELS = {
    0: "Rebote / Friccion",
    2: "Buscador Puntual",
}


def parse_args() -> argparse.Namespace:
    project_dir = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description="Join BauData usage results with the user/company master file.")
    parser.add_argument("--usage-file", default=str(project_dir / "outputs" / "kmeans_k3" / "resultados_clustering_posthog.csv"))
    parser.add_argument("--users-file", default=str(project_dir / "data" / "company_master" / "usuarios_baudata_2026-04-29.xlsx"))
    parser.add_argument("--output-dir", default=str(project_dir / "outputs" / "company_analysis"))
    return parser.parse_args()


def normalize_email(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().str.strip()


def normalize_company(series: pd.Series) -> pd.Series:
    return (
        series.fillna("Sin empresa informada")
        .astype(str)
        .str.strip()
        .str.replace(r"\s+", " ", regex=True)
        .str.lower()
    )


def load_inputs(usage_file: Path, users_file: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    usage = pd.read_csv(usage_file)
    users = pd.read_excel(users_file)

    usage["email_norm"] = normalize_email(usage["distinct_id"])
    users["email_norm"] = normalize_email(users["user"])
    users["empresa_norm"] = normalize_company(users["empresa"])
    users["status_norm"] = users["status"].fillna("sin_status").astype(str).str.lower().str.strip()

    numeric_cols = ["marker_select_count", "search_filter_select_count", "page_view_count", "download_flag", "real_duration"]
    for col in numeric_cols:
        usage[col] = pd.to_numeric(usage[col], errors="coerce").fillna(0)

    cluster_col = "cluster_label" if "cluster_label" in usage.columns else "cluster"
    usage["cluster_label"] = pd.to_numeric(usage[cluster_col], errors="coerce").fillna(-1).astype(int)
    usage["total_interacciones"] = usage["marker_select_count"] + usage["search_filter_select_count"]
    usage["ratio_clicks_vista"] = usage["total_interacciones"].div(usage["page_view_count"].replace(0, pd.NA)).fillna(0)
    return usage, users


def add_session_segment(usage: pd.DataFrame) -> pd.DataFrame:
    usage = usage.copy()
    usage["segmento_sesion"] = usage["cluster_label"].map(POWERBI_SEGMENT_LABELS).fillna("Otro")
    risk_mask = (usage["cluster_label"] == 1) & (usage["ratio_clicks_vista"] > 15)
    power_mask = usage["cluster_label"] == 1
    usage.loc[risk_mask, "segmento_sesion"] = "Riesgo (Rage Clicks)"
    usage.loc[power_mask & ~risk_mask, "segmento_sesion"] = "Power User (Validado)"
    return usage


def build_user_usage(usage: pd.DataFrame) -> pd.DataFrame:
    usage = add_session_segment(usage)
    grouped = usage.groupby("email_norm", as_index=False).agg(
        sesiones_totales=("email_norm", "size"),
        total_interacciones=("total_interacciones", "sum"),
        paginas_totales=("page_view_count", "sum"),
        descargas_sesiones=("download_flag", "sum"),
        duracion_total_s=("real_duration", "sum"),
        primera_sesion=("start", "min"),
        ultima_sesion=("start", "max"),
    )

    segment_counts = usage.pivot_table(
        index="email_norm",
        columns="segmento_sesion",
        values="start",
        aggfunc="count",
        fill_value=0,
    ).reset_index()
    user_usage = grouped.merge(segment_counts, on="email_norm", how="left")

    for col in ["Power User (Validado)", "Buscador Puntual", "Rebote / Friccion", "Riesgo (Rage Clicks)"]:
        if col not in user_usage.columns:
            user_usage[col] = 0

    user_usage["perfil_usuario"] = "Sin clasificar"
    user_usage.loc[user_usage["Rebote / Friccion"] > 0, "perfil_usuario"] = "Rebote / Friccion"
    user_usage.loc[user_usage["Buscador Puntual"] > 0, "perfil_usuario"] = "Buscador Puntual"
    user_usage.loc[user_usage["Power User (Validado)"] > 0, "perfil_usuario"] = "Power User (Validado)"

    duracion_min = (user_usage["duracion_total_s"] / 60).clip(upper=120)
    user_usage["score_oportunidad_activacion"] = pd.NA
    opportunity_mask = (user_usage["descargas_sesiones"] == 0) & (user_usage["total_interacciones"] >= 5)
    user_usage.loc[opportunity_mask, "score_oportunidad_activacion"] = (
        user_usage.loc[opportunity_mask, "total_interacciones"] * 2
        + user_usage.loc[opportunity_mask, "paginas_totales"]
        + duracion_min.loc[opportunity_mask] * 0.1
    )
    user_usage["score_valor_uso"] = (
        user_usage["descargas_sesiones"] * 20
        + user_usage["total_interacciones"] * 1.5
        + user_usage["paginas_totales"]
        + duracion_min * 0.2
    )

    user_usage["prioridad_comercial"] = "Baja / monitoreo"
    user_usage.loc[user_usage["perfil_usuario"] == "Rebote / Friccion", "prioridad_comercial"] = "Recuperacion"
    user_usage.loc[user_usage["descargas_sesiones"] > 0, "prioridad_comercial"] = "Uso confirmado"
    high_value = (user_usage["descargas_sesiones"] > 0) & (
        (user_usage["perfil_usuario"] == "Power User (Validado)") | (user_usage["score_valor_uso"] >= 50)
    )
    user_usage.loc[high_value, "prioridad_comercial"] = "Alto valor"
    user_usage.loc[user_usage["score_oportunidad_activacion"].fillna(0) >= 30, "prioridad_comercial"] = "Media activacion"
    user_usage.loc[user_usage["score_oportunidad_activacion"].fillna(0) >= 60, "prioridad_comercial"] = "Alta activacion"

    user_usage["accion_recomendada"] = "Monitorear"
    user_usage.loc[user_usage["perfil_usuario"] == "Rebote / Friccion", "accion_recomendada"] = "Reducir friccion / onboarding"
    activation = (user_usage["descargas_sesiones"] == 0) & (user_usage["total_interacciones"] >= 10) & (user_usage["paginas_totales"] >= 2)
    user_usage.loc[activation, "accion_recomendada"] = "Activar descarga / acompanar"
    user_usage.loc[user_usage["descargas_sesiones"] > 0, "accion_recomendada"] = "Mantener y profundizar uso"
    user_usage.loc[
        (user_usage["descargas_sesiones"] > 0) & (user_usage["perfil_usuario"] == "Power User (Validado)"),
        "accion_recomendada",
    ] = "Expandir / caso de exito"
    return user_usage


def build_user_company_table(users: pd.DataFrame, user_usage: pd.DataFrame) -> pd.DataFrame:
    enriched = users.merge(user_usage, on="email_norm", how="left")
    usage_cols = ["sesiones_totales", "total_interacciones", "paginas_totales", "descargas_sesiones", "duracion_total_s", "score_valor_uso"]
    for col in usage_cols:
        enriched[col] = pd.to_numeric(enriched[col], errors="coerce").fillna(0)

    enriched["tiene_uso"] = enriched["sesiones_totales"] > 0
    enriched["tiene_descarga"] = enriched["descargas_sesiones"] > 0
    enriched["usuario_activo"] = enriched["status_norm"].eq("activo")
    enriched["perfil_usuario"] = enriched["perfil_usuario"].fillna("Sin uso detectado")
    enriched["prioridad_comercial"] = enriched["prioridad_comercial"].fillna("Sin uso detectado")
    enriched["accion_recomendada"] = enriched["accion_recomendada"].fillna("Evaluar activacion / adopcion")
    return enriched


def build_company_summary(enriched: pd.DataFrame) -> pd.DataFrame:
    agg = enriched.groupby("empresa_norm", as_index=False).agg(
        empresa=("empresa", "first"),
        usuarios_registrados=("email_norm", "nunique"),
        usuarios_activos=("usuario_activo", "sum"),
        usuarios_inactivos=("status_norm", lambda values: (values == "inactivo").sum()),
        usuarios_con_uso=("tiene_uso", "sum"),
        usuarios_con_descarga=("tiene_descarga", "sum"),
        sesiones_totales=("sesiones_totales", "sum"),
        total_interacciones=("total_interacciones", "sum"),
        paginas_totales=("paginas_totales", "sum"),
        descargas_sesiones=("descargas_sesiones", "sum"),
        duracion_total_s=("duracion_total_s", "sum"),
        score_valor_uso=("score_valor_uso", "sum"),
        primera_sesion=("primera_sesion", "min"),
        ultima_sesion=("ultima_sesion", "max"),
    )

    active_usage = enriched.assign(activo_con_uso=enriched["usuario_activo"] & enriched["tiene_uso"]).groupby("empresa_norm")["activo_con_uso"].sum().reset_index(name="usuarios_activos_con_uso")
    priorities = enriched.pivot_table(index="empresa_norm", columns="prioridad_comercial", values="email_norm", aggfunc="count", fill_value=0).reset_index()
    actions = enriched.pivot_table(index="empresa_norm", columns="accion_recomendada", values="email_norm", aggfunc="count", fill_value=0).reset_index()

    summary = agg.merge(active_usage, on="empresa_norm", how="left")
    summary = summary.merge(priorities, on="empresa_norm", how="left")
    summary = summary.merge(actions, on="empresa_norm", how="left")
    summary["usuarios_sin_uso"] = summary["usuarios_registrados"] - summary["usuarios_con_uso"]
    summary["usuarios_activos_sin_uso"] = summary["usuarios_activos"] - summary["usuarios_activos_con_uso"]
    summary["tasa_usuarios_con_uso"] = summary["usuarios_con_uso"].div(summary["usuarios_registrados"]).fillna(0)
    summary["tasa_activos_con_uso"] = summary["usuarios_activos_con_uso"].div(summary["usuarios_activos"].replace(0, pd.NA)).fillna(0)
    summary["tasa_usuarios_con_descarga"] = summary["usuarios_con_descarga"].div(summary["usuarios_registrados"]).fillna(0)
    summary["interacciones_por_usuario_activo"] = summary["total_interacciones"].div(summary["usuarios_activos"].replace(0, pd.NA)).fillna(0)

    for col in ["Alta activacion", "Media activacion", "Alto valor", "Recuperacion", "Uso confirmado", "Sin uso detectado"]:
        if col not in summary.columns:
            summary[col] = 0

    summary["estado_uso_empresa"] = "Con uso"
    summary.loc[summary["usuarios_activos"] == 0, "estado_uso_empresa"] = "Sin usuarios activos"
    summary.loc[(summary["usuarios_activos"] > 0) & (summary["usuarios_activos_con_uso"] == 0), "estado_uso_empresa"] = "Activa sin uso detectado"
    summary.loc[(summary["usuarios_activos"] > 0) & (summary["usuarios_activos_con_uso"] > 0) & (summary["usuarios_con_descarga"] == 0), "estado_uso_empresa"] = "Uso sin descarga"

    summary["prioridad_empresa"] = "Monitorear"
    summary.loc[summary["estado_uso_empresa"].eq("Sin usuarios activos"), "prioridad_empresa"] = "Revisar contrato / usuarios activos"
    summary.loc[summary["estado_uso_empresa"].eq("Activa sin uso detectado"), "prioridad_empresa"] = "Activar empresa sin uso"
    summary.loc[summary["Recuperacion"] > 0, "prioridad_empresa"] = "Reducir friccion / recuperar"
    summary.loc[summary["Media activacion"] > 0, "prioridad_empresa"] = "Activacion media"
    summary.loc[summary["Alta activacion"] > 0, "prioridad_empresa"] = "Activacion alta"
    summary.loc[summary["Alto valor"] > 0, "prioridad_empresa"] = "Expandir / profundizar"

    summary["score_prioridad_empresa"] = (
        summary["usuarios_activos_sin_uso"] * 20
        + summary["Alta activacion"] * 15
        + summary["Media activacion"] * 8
        + summary["Recuperacion"] * 4
        + summary["Alto valor"] * 3
    )
    return summary.sort_values(["score_prioridad_empresa", "usuarios_activos_sin_uso"], ascending=False)


def export_powerbi_tables(company_summary: pd.DataFrame, enriched: pd.DataFrame, output_dir: Path) -> None:
    powerbi_cols = {
        "empresa": "Empresa",
        "empresa_norm": "Empresa_Key",
        "estado_uso_empresa": "Estado_Uso_Empresa",
        "prioridad_empresa": "Prioridad_Empresa",
        "score_prioridad_empresa": "Score_Prioridad_Empresa",
        "usuarios_registrados": "Usuarios_Registrados",
        "usuarios_activos": "Usuarios_Activos",
        "usuarios_inactivos": "Usuarios_Inactivos",
        "usuarios_con_uso": "Usuarios_Con_Uso",
        "usuarios_activos_con_uso": "Usuarios_Activos_Con_Uso",
        "usuarios_sin_uso": "Usuarios_Sin_Uso",
        "usuarios_activos_sin_uso": "Usuarios_Activos_Sin_Uso",
        "usuarios_con_descarga": "Usuarios_Con_Descarga",
        "sesiones_totales": "Sesiones_Totales",
        "total_interacciones": "Total_Interacciones",
        "paginas_totales": "Paginas_Totales",
        "descargas_sesiones": "Descargas_Sesiones",
        "score_valor_uso": "Score_Valor_Uso",
        "tasa_usuarios_con_uso": "Tasa_Usuarios_Con_Uso",
        "tasa_activos_con_uso": "Tasa_Activos_Con_Uso",
        "tasa_usuarios_con_descarga": "Tasa_Usuarios_Con_Descarga",
        "interacciones_por_usuario_activo": "Interacciones_Por_Usuario_Activo",
        "primera_sesion": "Primera_Sesion",
        "ultima_sesion": "Ultima_Sesion",
        "Alta activacion": "Usuarios_Alta_Activacion",
        "Media activacion": "Usuarios_Media_Activacion",
        "Alto valor": "Usuarios_Alto_Valor",
        "Recuperacion": "Usuarios_Recuperacion",
        "Uso confirmado": "Usuarios_Uso_Confirmado",
        "Sin uso detectado": "Usuarios_Sin_Uso_Detectado",
    }
    company_summary_powerbi = company_summary[[col for col in powerbi_cols if col in company_summary.columns]].rename(columns=powerbi_cols)
    company_summary_powerbi.to_csv(output_dir / "empresas_powerbi.csv", index=False, encoding="utf-8-sig")

    user_powerbi_cols = {
        "id_usuario": "Id_Usuario",
        "user": "Email_Usuario",
        "email_norm": "Email_Key",
        "empresa": "Empresa",
        "empresa_norm": "Empresa_Key",
        "status_norm": "Status_Usuario",
        "usuario_activo": "Usuario_Activo",
        "tiene_uso": "Tiene_Uso",
        "tiene_descarga": "Tiene_Descarga",
        "perfil_usuario": "Perfil_Usuario",
        "prioridad_comercial": "Prioridad_Comercial",
        "accion_recomendada": "Accion_Recomendada",
        "sesiones_totales": "Sesiones_Totales",
        "total_interacciones": "Total_Interacciones",
        "paginas_totales": "Paginas_Totales",
        "descargas_sesiones": "Descargas_Sesiones",
        "score_oportunidad_activacion": "Score_Oportunidad_Activacion",
        "score_valor_uso": "Score_Valor_Uso",
    }
    user_company_powerbi = enriched[[col for col in user_powerbi_cols if col in enriched.columns]].rename(columns=user_powerbi_cols)
    for col in ["Sesiones_Totales", "Total_Interacciones", "Paginas_Totales", "Descargas_Sesiones", "Score_Oportunidad_Activacion", "Score_Valor_Uso"]:
        if col in user_company_powerbi.columns:
            user_company_powerbi[col] = pd.to_numeric(user_company_powerbi[col], errors="coerce").fillna(0).round().astype("Int64")
    user_company_powerbi.to_csv(output_dir / "usuarios_empresas_powerbi.csv", index=False, encoding="utf-8-sig")


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    usage, users = load_inputs(Path(args.usage_file), Path(args.users_file))
    user_usage = build_user_usage(usage)
    enriched = build_user_company_table(users, user_usage)
    company_summary = build_company_summary(enriched)

    is_email_usage = user_usage["email_norm"].str.contains("@", na=False)
    unmatched_usage = user_usage.loc[is_email_usage & ~user_usage["email_norm"].isin(users["email_norm"])].copy()
    non_email_usage = user_usage.loc[~is_email_usage].copy()
    companies_without_use = company_summary.query("estado_uso_empresa == 'Activa sin uso detectado'").copy()

    enriched.to_csv(output_dir / "usuarios_empresas_enriquecido.csv", index=False, encoding="utf-8-sig")
    company_summary.to_csv(output_dir / "empresas_resumen_uso.csv", index=False, encoding="utf-8-sig")
    companies_without_use.to_csv(output_dir / "empresas_activas_sin_uso.csv", index=False, encoding="utf-8-sig")
    unmatched_usage.to_csv(output_dir / "usuarios_con_uso_sin_match_empresa.csv", index=False, encoding="utf-8-sig")
    non_email_usage.to_csv(output_dir / "ids_no_email_con_uso.csv", index=False, encoding="utf-8-sig")
    export_powerbi_tables(company_summary, enriched, output_dir)

    print("=" * 70)
    print("Company analysis generated")
    print(f"Master users: {len(users)}")
    print(f"Master companies: {users['empresa_norm'].nunique()}")
    print(f"Users with detected use in master: {enriched['tiene_uso'].sum()}")
    print(f"Active users without detected use: {enriched.query('usuario_activo and not tiene_uso').shape[0]}")
    print(f"Active companies without detected use: {len(companies_without_use)}")
    print(f"E-mail IDs with usage but no company match: {len(unmatched_usage)}")
    print(f"Non-email IDs with usage: {len(non_email_usage)}")
    print(f"Output: {output_dir}")


if __name__ == "__main__":
    main()

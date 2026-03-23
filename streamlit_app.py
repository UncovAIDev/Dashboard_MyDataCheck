import base64
import hmac
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

import altair as alt
import pandas as pd
import requests
import streamlit as st

st.set_page_config(
    page_title="Credits Dashboard",
    page_icon="C",
    layout="wide",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"], .stApp, .stMarkdown, .stMetric,
    .stDataFrame, .stSelectbox, button, input, label, p, span, div {
        font-family: 'Inter', sans-serif !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

COLORS = {
    "CHART_1": "#03be9c",
    "CHART_2": "#0080ff",
    "CHART_3": "#ff6b6b",
    "CHART_4": "#9B59B6",
    "CHART_5": "#075e54",
}

TYPE_DOMAIN = ["Image", "Video"]
TYPE_COLORS = [
    COLORS["CHART_1"],
    COLORS["CHART_2"],
]


def get_required_secret(key: str) -> str:
    value = st.secrets.get(key)
    if value is None or str(value).strip() == "":
        st.error(f"Secret manquant: `{key}`")
        st.info(
            "Ajoute les secrets requis dans `.streamlit/secrets.toml` puis recharge la page."
        )
        st.stop()
    return str(value)


def check_password() -> None:
    if st.session_state.get("is_authenticated", False):
        return

    expected_password = str(st.secrets.get("DASHBOARD_PASSWORD", ""))
    if not expected_password:
        st.error("Secret manquant: `DASHBOARD_PASSWORD`")
        st.info(
            "Ajoute `DASHBOARD_PASSWORD` dans `.streamlit/secrets.toml` puis recharge la page."
        )
        st.stop()

    st.title("Dashboard Credits")
    st.write("Saisis le mot de passe pour acceder au dashboard.")

    with st.form("password_form", clear_on_submit=False):
        entered_password = st.text_input("Mot de passe", type="password")
        submitted = st.form_submit_button("Se connecter", type="primary")

    if submitted:
        if hmac.compare_digest(entered_password, expected_password):
            st.session_state.is_authenticated = True
            st.rerun()
        st.error("Mot de passe incorrect.")

    st.stop()


def fetch_credits_data(api_url: str, user_api_key: str) -> dict[str, Any]:
    endpoint_url = f"{api_url.rstrip('/')}/get-credits-api"
    response = requests.get(
        endpoint_url,
        headers={"x-api-key": user_api_key},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("Le endpoint doit retourner un objet JSON.")
    return payload


def cents_to_eur_label(value_cents: Any) -> str:
    value = int(value_cents or 0)
    return f"{value / 100:.2f} EUR"


def format_iso_datetime(value: Any) -> str:
    if not value:
        return "-"
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return str(value)


def build_usage_summary_rows(usage: list[dict[str, Any]]) -> list[dict[str, Any]]:
    endpoint_stats: dict[str, dict[str, int]] = defaultdict(
        lambda: {"calls": 0, "cost_cents": 0}
    )

    for item in usage:
        endpoint = str(item.get("endpoint") or "unknown")
        cost_cents = int(item.get("cost_cents") or 0)
        endpoint_stats[endpoint]["calls"] += 1
        endpoint_stats[endpoint]["cost_cents"] += cost_cents

    rows: list[dict[str, Any]] = []
    for endpoint, stats in sorted(
        endpoint_stats.items(), key=lambda x: x[1]["cost_cents"], reverse=True
    ):
        rows.append(
            {
                "endpoint": endpoint,
                "calls": stats["calls"],
                "cost": cents_to_eur_label(stats["cost_cents"]),
            }
        )
    return rows


def parse_usage_type(endpoint: Any) -> str | None:
    endpoint_value = str(endpoint or "").lower()
    if "image" in endpoint_value:
        return "Image"
    if "video" in endpoint_value:
        return "Video"
    return None


def to_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def build_usage_dataframe(usage: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for item in usage:
        dt = to_datetime(item.get("date"))
        usage_type = parse_usage_type(item.get("endpoint"))
        if dt is None or usage_type is None:
            continue
        rows.append(
            {
                "date": dt.date(),
                "type": usage_type,
                "cost_cents": int(item.get("cost_cents") or 0),
            }
        )
    return pd.DataFrame(rows)


def get_logo_base64(path: str = "images/logo.png") -> str:
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        return ""


def render_dashboard_header() -> bool:
    refresh_clicked = False
    updated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    logo_b64 = get_logo_base64()
    logo_html = (
        f'<img src="data:image/png;base64,{logo_b64}" style="height:48px; width:auto; flex-shrink:0;" />'
        if logo_b64
        else ""
    )

    header_html = (
        '<div style="display:flex;align-items:center;justify-content:space-between;'
        'padding:1.1rem 1.4rem 1rem 1.4rem;background:#ffffff;border:1px solid #e8ecf0;'
        'border-radius:12px;margin-bottom:0.5rem;gap:1rem;">'
        '<div style="display:flex;align-items:center;gap:1rem;flex:1;min-width:0;">'
        + logo_html
        + '<div style="min-width:0;">'
        '<div style="font-size:1.35rem;font-weight:700;color:#0f172a;line-height:1.2;'
        "white-space:nowrap;font-family:'Inter',sans-serif;\">Credits API Dashboard</div>"
        '<div style="font-size:0.82rem;color:#64748b;margin-top:0.15rem;'
        "font-family:'Inter',sans-serif;\">Suivi des credits, du volume de requetes et des depenses.</div>"
        "</div></div>"
        '<div style="display:flex;flex-direction:column;align-items:flex-end;gap:0.4rem;flex-shrink:0;">'
        '<span style="display:inline-flex;align-items:center;gap:0.35rem;padding:0.3rem 0.75rem;'
        "border-radius:999px;background:#e6faf6;color:#03be9c;font-weight:600;font-size:0.76rem;"
        "font-family:'Inter',sans-serif;letter-spacing:0.02em;border:1px solid #b2edd9;\">"
        '<span style="width:6px;height:6px;border-radius:50%;background:#03be9c;display:inline-block;"></span>'
        "Live</span>"
        f'<span style="font-size:0.75rem;color:#94a3b8;font-family:\'Inter\',sans-serif;">Updated {updated_at}</span>'
        "</div></div>"
    )

    st.markdown(header_html, unsafe_allow_html=True)

    refresh_clicked = st.button(
        "Rafraichir",
        type="secondary",
        key="header_refresh_button",
    )

    return refresh_clicked


def filter_usage_period(df: pd.DataFrame, days: int | None) -> pd.DataFrame:
    if df.empty or days is None:
        return df
    cutoff = datetime.utcnow().date() - timedelta(days=days - 1)
    return df[df["date"] >= cutoff]


def display_usage_charts(usage: list[dict[str, Any]]) -> None:
    st.subheader("Usage charts")
    if not usage:
        st.info("Aucune donnee d'usage pour les graphiques.")
        return

    time_period_options = {
        "1 Month": 30,
        "2 Months": 60,
        "3 Months": 90,
        "All Time": None,
    }
    selected_period = st.selectbox(
        "Select time period:",
        options=list(time_period_options.keys()),
        index=1,
        key="usage_chart_time_filter",
    )
    filtered_days = time_period_options[selected_period]

    df_usage = build_usage_dataframe(usage)
    df_usage = filter_usage_period(df_usage, filtered_days)

    if df_usage.empty:
        st.info("Aucune donnee d'usage sur la periode selectionnee.")
        return

    counts_by_day = (
        df_usage.groupby(["date", "type"], as_index=False)
        .size()
        .rename(columns={"size": "count"})
    )

    spend_by_day = (
        df_usage.groupby(["date", "type"], as_index=False)["cost_cents"].sum()
    )
    spend_by_day["spent_eur"] = spend_by_day["cost_cents"] / 100

    total_spend_by_day = df_usage.groupby(["date"], as_index=False)["cost_cents"].sum()
    total_spend_by_day["spent_eur"] = total_spend_by_day["cost_cents"] / 100

    chart_col_1, chart_col_2 = st.columns(2)

    with chart_col_1:
        requests_chart = (
            alt.Chart(counts_by_day)
            .mark_bar()
            .encode(
                x=alt.X("date:T", title="Date", axis=alt.Axis(format="%m-%d")),
                y=alt.Y("count:Q", title="Number of Requests", stack="zero"),
                color=alt.Color(
                    "type:N",
                    title="Request Type",
                    scale=alt.Scale(domain=TYPE_DOMAIN, range=TYPE_COLORS),
                ),
                order=alt.Order("type:N", sort="descending"),
                tooltip=[
                    alt.Tooltip("date:T", title="Date", format="%Y-%m-%d"),
                    alt.Tooltip("type:N", title="Type"),
                    alt.Tooltip("count:Q", title="Requests"),
                ],
            )
            .properties(
                height=380,
                title="Requests by Type - Daily Stacked View",
            )
            .interactive()
        )
        st.altair_chart(requests_chart, use_container_width=True)

    with chart_col_2:
        spend_area = (
            alt.Chart(spend_by_day)
            .mark_area(opacity=0.75, interpolate="monotone")
            .encode(
                x=alt.X("date:T", title="Date", axis=alt.Axis(format="%m-%d")),
                y=alt.Y("spent_eur:Q", title="Spent (EUR)", stack="zero"),
                color=alt.Color(
                    "type:N",
                    title="Request Type",
                    scale=alt.Scale(domain=TYPE_DOMAIN, range=TYPE_COLORS),
                ),
                order=alt.Order("type:N", sort="descending"),
                tooltip=[
                    alt.Tooltip("date:T", title="Date", format="%Y-%m-%d"),
                    alt.Tooltip("type:N", title="Type"),
                    alt.Tooltip("spent_eur:Q", title="Spent (EUR)", format=".2f"),
                ],
            )
            .properties(
                height=380,
                title="Spend by Type - Daily Stacked Area",
            )
        )

        total_spend_line = (
            alt.Chart(total_spend_by_day)
            .mark_line(color=COLORS["CHART_5"], strokeWidth=3)
            .encode(
                x=alt.X("date:T"),
                y=alt.Y("spent_eur:Q"),
                tooltip=[
                    alt.Tooltip("date:T", title="Date", format="%Y-%m-%d"),
                    alt.Tooltip("spent_eur:Q", title="Total Spent (EUR)", format=".2f"),
                ],
            )
        )

        st.altair_chart((spend_area + total_spend_line).interactive(), use_container_width=True)


def main() -> None:
    check_password()

    api_url = get_required_secret("API_URL")
    user_api_key = get_required_secret("USER_API_KEY")

    refresh_clicked = render_dashboard_header()

    if refresh_clicked:
        try:
            st.session_state.credits_data = fetch_credits_data(api_url=api_url, user_api_key=user_api_key)
        except requests.HTTPError as err:
            status = err.response.status_code if err.response is not None else "n/a"
            st.error(f"Echec de la requete `/get-credits-api` (HTTP {status}).")
            st.stop()
        except requests.RequestException as err:
            st.error(f"Impossible de joindre l'API: {err}")
            st.stop()
        except ValueError as err:
            st.error(str(err))
            st.stop()

    if "credits_data" not in st.session_state:
        st.info("Cliquez sur Rafraichir pour charger les données.")
        st.stop()

    data = st.session_state.credits_data

    balance_cents = int(data.get("balance_cents") or 0)
    topped_up_cents = int(data.get("total_topped_up_cents") or 0)
    spent_cents = int(data.get("total_spent_cents") or 0)
    total_requests = int(data.get("total_requests") or 0)
    usage = data.get("usage") or []
    payments = data.get("payments") or []

    today = datetime.now(tz=timezone.utc).date()
    calls_today = sum(
        1 for item in usage
        if (dt := to_datetime(item.get("date"))) is not None and dt.date() == today
    )

    metric_col_1, metric_col_2, metric_col_3, metric_col_4, metric_col_5 = st.columns(5)
    metric_col_1.metric("Balance", cents_to_eur_label(balance_cents))
    metric_col_2.metric("Total rechargé", cents_to_eur_label(topped_up_cents))
    metric_col_3.metric("Total dépensé", cents_to_eur_label(spent_cents))
    metric_col_4.metric("Appels API", total_requests)
    metric_col_5.metric("Appels aujourd'hui", calls_today)

    display_usage_charts(usage)

    st.subheader("Usage summary")
    if usage:
        st.dataframe(
            build_usage_summary_rows(usage),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Aucune donnee d'usage.")

    st.subheader("Usage history")
    if usage:
        sorted_usage = sorted(
            usage, key=lambda item: str(item.get("date") or ""), reverse=True
        )
        rows = [
            {
                "date": format_iso_datetime(item.get("date")),
                "endpoint": item.get("endpoint", "unknown"),
                "cost": cents_to_eur_label(item.get("cost_cents")),
            }
            for item in sorted_usage
        ]
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("Aucune entree dans l'historique d'usage.")

    st.subheader("Payments")
    if payments:
        payment_rows = [
            {
                "date": format_iso_datetime(p.get("date")),
                "montant": cents_to_eur_label(p.get("amount_cents")),
                "statut": p.get("status", "-"),
            }
            for p in payments
        ]
        st.dataframe(payment_rows, use_container_width=True, hide_index=True)
    else:
        st.info("Aucun paiement enregistre.")


if __name__ == "__main__":
    main()

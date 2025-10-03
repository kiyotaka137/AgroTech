# dash_acids_dark.py
import pandas as pd
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output
import dash_bootstrap_components as dbc

# --- ДАННЫЕ ---
DATA = {
    "acid": [1, 2, 3, 4, 5],
    "value": [7.5, 4.2, 6.8, 8.9, 5.1],
    "lower": [6.0, 3.5, 5.0, 7.0, 4.5],
    "upper": [8.0, 5.0, 7.0, 9.5, 6.0],
}

def prepare_df(data):
    df = pd.DataFrame(data)
    df['inside'] = df.apply(lambda r: r['lower'] <= r['value'] <= r['upper'], axis=1)
    return df

def create_figure(df, show_ranges=True, scheme='green_red', marker_size=14, y_range=None):
    fig = go.Figure()

    # диапазоны (полупрозрачные прямоугольники)
    if show_ranges:
        half_width = 0.25
        for _, r in df.iterrows():
            fig.add_shape(
                type="rect",
                x0=r['acid'] - half_width, x1=r['acid'] + half_width,
                y0=r['lower'], y1=r['upper'],
                fillcolor="rgba(100,200,255,0.25)",
                line=dict(width=0),
                layer="below"
            )

    # цвета точек
    if scheme == 'green_red':
        colors = ['#2ecc71' if v else '#e74c3c' for v in df['inside']]
    else:
        colors = ['#ecf0f1' if v else '#e74c3c' for v in df['inside']]

    hover_texts = [
        f"<b>Кислота:</b> {a}<br>"
        f"<b>Значение:</b> {v}<br>"
        f"<b>Допустимый диапазон:</b> {lo} – {hi}"
        for a, v, lo, hi in zip(df['acid'], df['value'], df['lower'], df['upper'])
    ]

    fig.add_trace(go.Scatter(
        x=df['acid'],
        y=df['value'],
        mode="markers",
        marker=dict(size=marker_size, color=colors,
                    line=dict(width=1, color='black'),
                    sizemode="diameter"),
        text=hover_texts,
        hoverinfo="text",
        name="Измерения"
    ))

    # оформление
    yaxis = dict(title="Показатель", gridcolor="rgba(255,255,255,0.15)", zeroline=False)
    if y_range:
        yaxis['range'] = [y_range[0], y_range[1]]

    fig.update_layout(
        title=dict(text="Измерения кислот и допустимые диапазоны", x=0.02, xanchor='left'),
        xaxis=dict(title="Номер кислоты", tickmode="array", tickvals=df['acid'], zeroline=False),
        yaxis=yaxis,
        template="plotly_dark",
        margin=dict(l=40, r=20, t=70, b=40),
        hoverlabel=dict(bgcolor="black", font_size=12, font_color="white"),
        transition_duration=400
    )

    return fig

# --- ПОДГОТОВКА ---
df = prepare_df(DATA)
y_min = min(df['lower'].min(), df['value'].min()) - 1
y_max = max(df['upper'].max(), df['value'].max()) + 1

# --- DASH ---
app = Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])
server = app.server

controls = dbc.Card(
    body=True,
    children=[
        html.H5("⚙️ Настройки", className="card-title"),
        dbc.Checklist(
            id="show-ranges",
            options=[{"label": "Показать диапазоны", "value": "show"}],
            value=["show"],
            switch=True,
        ),
        html.Br(),
        dbc.RadioItems(
            id="color-scheme",
            options=[
                {"label": "Зелёный / Красный", "value": "green_red"},
                {"label": "Белый / Красный", "value": "black_red"},
            ],
            value="green_red",
            className="mb-3"
        ),
        html.Label("Размер маркеров"),
        dcc.Slider(id="marker-size", min=6, max=30, step=1, value=14,
                   marks={6: "6", 14: "14", 24: "24", 30: "30"}),
        html.Br(),
        html.Label("Диапазон по оси Y"),
        dcc.RangeSlider(
            id="y-range",
            min=y_min, max=y_max, step=0.2,
            value=[y_min, y_max],
            allowCross=False,
            tooltip={"placement": "bottom"}
        ),
    ]
)

app.layout = dbc.Container(
    fluid=True,
    children=[
        html.H2("🧪 Визуализация кислот", className="my-3"),
        dbc.Row([
            dbc.Col(controls, md=3, xs=12, className="mb-3"),
            dbc.Col(dcc.Graph(id="acid-graph", config={"displayModeBar": True}), md=9, xs=12),
        ])
    ]
)

# --- CALLBACK ---
@app.callback(
    Output("acid-graph", "figure"),
    Input("show-ranges", "value"),
    Input("color-scheme", "value"),
    Input("marker-size", "value"),
    Input("y-range", "value"),
)
def update_figure(show_values, scheme, marker_size, y_range):
    show_ranges = "show" in (show_values or [])
    yr = tuple(y_range) if y_range and len(y_range) == 2 else None
    return create_figure(df, show_ranges=show_ranges, scheme=scheme, marker_size=marker_size, y_range=yr)

if __name__ == "__main__":
    app.run(debug=True)

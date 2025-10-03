# graphs/graph1/version1/plotly_example.py
import pandas as pd
import plotly.graph_objects as go
#можно интегрировать Plotly в PyQt через QWebEngine
def plot_acid_measurements_plotly(data):
    """
    Интерактивный Plotly-график:
    - вертикальные толстые линии = допустимые диапазоны (с прозрачностью)
    - "шапки" на концах диапазонов
    - точки измерений (чёрные/красные в зависимости от попадания)
    """
    if isinstance(data, dict):
        df = pd.DataFrame(data)
    else:
        df = data.copy()

    df['inside'] = df.apply(lambda r: r['lower'] <= r['value'] <= r['upper'], axis=1)

    fig = go.Figure()

    # Диапазоны: для прозрачности используем параметр opacity у трассы
    for _, r in df.iterrows():
        # толстая вертикальная полоса (линия) с прозрачностью
        fig.add_trace(go.Scatter(
            x=[r['acid'], r['acid']],
            y=[r['lower'], r['upper']],
            mode="lines",
            line=dict(color="blue", width=20),  # без opacity тут
            opacity=0.25,                        # а opacity — у трассы
            hoverinfo="skip",
            showlegend=False
        ))

        # "шапки" на концах диапазонов
        fig.add_trace(go.Scatter(
            x=[r['acid'] - 0.12, r['acid'] + 0.12],
            y=[r['lower'], r['lower']],
            mode="lines",
            line=dict(color="blue", width=2),
            hoverinfo="skip",
            showlegend=False
        ))
        fig.add_trace(go.Scatter(
            x=[r['acid'] - 0.12, r['acid'] + 0.12],
            y=[r['upper'], r['upper']],
            mode="lines",
            line=dict(color="blue", width=2),
            hoverinfo="skip",
            showlegend=False
        ))

    # Точки измерений: цвет зависит от попадания в диапазон
    colors = ['black' if v else 'red' for v in df['inside']]
    hover_texts = [
        f"acid: {a}<br>value: {v}<br>range: {lo}–{hi}"
        for a, v, lo, hi in zip(df['acid'], df['value'], df['lower'], df['upper'])
    ]

    fig.add_trace(go.Scatter(
        x=df['acid'],
        y=df['value'],
        mode="markers",
        marker=dict(size=14, color=colors),
        text=hover_texts,
        hoverinfo="text",
        showlegend=False
    ))

    fig.update_layout(
        title="Измерения кислот и допустимые диапазоны",
        xaxis=dict(title="Номер кислоты", tickmode="array", tickvals=df['acid']),
        yaxis=dict(title="Показатель"),
        template="simple_white",
        margin=dict(l=40, r=20, t=60, b=40)
    )

    fig.show()


if __name__ == "__main__":
    data = {
        "acid": [1, 2, 3, 4, 5],
        "value": [7.5, 4.2, 6.8, 8.9, 5.1],
        "lower": [6.0, 3.5, 5.0, 7.0, 4.5],
        "upper": [8.0, 5.0, 7.0, 9.5, 6.0],
    }
    plot_acid_measurements_plotly(data)

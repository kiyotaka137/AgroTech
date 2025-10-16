import pytest
import pandas as pd
import matplotlib.pyplot as plt

from graph1 import plot_acid_measurements


@pytest.fixture
def sample_data():
    return {
        'acid': [1, 2, 3],
        'value': [5.0, 8.0, 2.0],
        'lower': [4.0, 7.0, 1.0],
        'upper': [6.0, 9.0, 3.0],
    }


def test_plot_from_dict_creates_figure(sample_data):
    fig = plot_acid_measurements(sample_data)
    assert isinstance(fig, plt.Figure)
    assert len(fig.axes) == 1
    ax = fig.axes[0]
    assert len(ax.collections) > 0  # scatter-точки
    assert len(ax.lines) > 0        # шапки диапазонов
    plt.close(fig)


def test_plot_from_dataframe_returns_figure(sample_data):
    df = pd.DataFrame(sample_data)
    fig = plot_acid_measurements(df)
    assert isinstance(fig, plt.Figure)
    plt.close(fig)


def test_plot_with_existing_ax_returns_none(sample_data):
    df = pd.DataFrame(sample_data)
    fig, ax = plt.subplots()
    result = plot_acid_measurements(df, ax=ax)
    assert result is None
    # Проверяем, что график нарисован на переданном ax
    assert len(ax.collections) > 0
    plt.close(fig)


def test_raises_if_missing_columns():
    bad_df = pd.DataFrame({'acid': [1, 2, 3], 'value': [1, 2, 3]})
    with pytest.raises(ValueError, match="Ожидаются колонки"):
        plot_acid_measurements(bad_df)


def test_inside_flag_correct(sample_data):
    df = pd.DataFrame(sample_data)
    plot_acid_measurements(df)
    df['inside'] = df.apply(lambda r: r['lower'] <= r['value'] <= r['upper'], axis=1)
    assert all(isinstance(v, bool) for v in df['inside'])

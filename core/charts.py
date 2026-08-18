"""Small shared Plotly helpers.

`add_vline`/`add_hline` with `annotation_text` triggers a plotly/pandas
incompatibility when the axis value is a pandas Timestamp (plotly tries to
average two Timestamps internally, which recent pandas no longer allows).
`labelled_vline` sidesteps it by adding the line and its label as two
separate, simple calls.
"""
from __future__ import annotations


def labelled_vline(fig, x, color: str, text: str, y: float = 1.02) -> None:
    fig.add_vline(x=x, line_dash="dash", line_color=color)
    fig.add_annotation(x=x, y=y, yref="paper", showarrow=False, text=text, font=dict(color=color, size=11))

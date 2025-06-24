import dash
from dash import dcc, html

from django_plotly_dash import DjangoDash

import plotly.express as px
import pandas as pd

app = DjangoDash('PolarRoute')


# assume you have a "long-form" data frame
# see https://plotly.com/python/px-arguments/ for more options
df = pd.DataFrame({
    "Fruit": ["Apples", "Oranges", "Bananas", "Apples", "Oranges", "Bananas"],
    "Amount": [4, 1, 2, 2, 4, 5],
    "City": ["SF", "SF", "SF", "Montreal", "Montreal", "Montreal"]
})

fig = px.bar(df, x="Fruit", y="Amount", color="City", barmode="group")

app.layout = html.Div(children=[
    html.H1(children='Hello Dash'),

    html.Div(children='''
        Dash: A web application framework for your data.
    '''),

    dcc.Graph(
        id='example-graph',
        figure=fig
    )
])


# app.layout = html.Div([
#     dcc.RadioItems(
#         id='dropdown-color',
#         options=[{'label': c, 'value': c.lower()} for c in ['Red', 'Green', 'Blue']],
#         value='red'
#     ),
#     html.Div(id='output-color'),
#     dcc.RadioItems(
#         id='dropdown-size',
#         options=[{'label': i, 'value': j} for i, j in [('L','large'), ('M','medium'), ('S','small')]],
#         value='medium'
#     ),
#     html.Div(id='output-size')

# ])

# @app.callback(
#     dash.dependencies.Output('output-color', 'children'),
#     [dash.dependencies.Input('dropdown-color', 'value')])
# def callback_color(dropdown_value):
#     return "The selected color is %s." % dropdown_value

# @app.callback(
#     dash.dependencies.Output('output-size', 'children'),
#     [dash.dependencies.Input('dropdown-color', 'value'),
#      dash.dependencies.Input('dropdown-size', 'value')])
# def callback_size(dropdown_color, dropdown_size):
#     return "The chosen T-shirt is a %s %s one." %(dropdown_size,
#                                                   dropdown_color)

if __name__ == '__main__':
    app.run(debug=True)
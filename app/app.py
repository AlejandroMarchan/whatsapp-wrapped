import dash_mantine_components as dmc
import dash_bootstrap_components as dbc
from dash_extensions.enrich import Input, Output, State, html, dcc
from dash_extensions.enrich import DashProxy, MultiplexerTransform, LogTransform, NoOutputTransform
import logging
import sys
import os
import calendar
import pandas as pd
import plotly.express as px
from .chat_processor.utils import extract_messages_from_chat, get_words_df

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'


# Init logging
logging.basicConfig(
    format='[%(asctime)s] [%(name)s:%(lineno)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S %z',
    stream=sys.stdout,
    level=10
)

log = logging.getLogger("app")
log.setLevel(logging.INFO)


app = DashProxy(
    __name__,
    title="WhatsApp Wrapped",
    transforms=[
        # makes it possible to target an output multiple times in callbacks
        MultiplexerTransform(),
        NoOutputTransform(),
        LogTransform()  # makes it possible to write log messages to a Dash component
    ],
    external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.FONT_AWESOME],
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1"},
    ],
)
app.config.suppress_callback_exceptions = True
server = app.server

app.layout = html.Div(
    [
        dcc.Store(id="words-store"),
        dbc.Row(
            [
                dbc.Col(
                    html.H1(["Welcome to WhatsApp Wrapped"]),
                    width="auto"
                ),
            ],
            justify="center",
            align="center",
            style={
                'margin-top': '15px',
                'text-align': 'center'
            }
        ),
        dbc.Row(
            [
                dbc.Col(
                    [
                        dcc.Upload(
                            id='upload-chat',
                            children=html.Div(
                                [
                                    'Drop or ',
                                    html.A('Select the exported chat (ZIP)', style={
                                           "cursor": "pointer", 'color': 'var(--bs-primary)'})
                                ]
                            ),
                            accept="zip,application/octet-stream,application/zip,application/x-zip,application/x-zip-compressed",
                        )
                    ],
                    width="12"
                ),
            ],
            justify="center",
            align="center",
            style={
                'margin-bottom': '20px',
                'margin-top': '15px'
            }
        ),
        html.Div(
            [
                dbc.Row(
                    [
                        html.H4(
                            id='n-messages',
                            style={
                                'margin-top': '35px',
                                'text-align': 'center'
                            }
                        ),
                        dcc.Loading(
                            dcc.Graph(
                                id='n-messages-by-person-graph',
                            ),
                        ),
                    ]
                ),
                dbc.Row(
                    [
                        dcc.Loading(
                            dcc.Graph(
                                id='n-messages-by-month-and-person-graph',
                            ),
                        )
                    ]
                ),
                dbc.Row(
                    [
                        dcc.Loading(
                            dcc.Graph(
                                id='n-messages-by-year-and-person-graph',
                            ),
                        )
                    ]
                ),
                dbc.Row(
                    [
                        dcc.Loading(
                            dcc.Graph(
                                id='n-messages-by-hour-and-person-graph',
                            ),
                        )
                    ]
                ),
                dbc.Row(
                    [
                        html.H4(
                            id='n-words',
                            style={
                                'margin-top': '35px',
                                'text-align': 'center'
                            }
                        ),
                        dcc.Loading(
                            dcc.Graph(
                                id='most-repeated-words-graph',
                            ),
                        )
                    ]
                ),
                dbc.Row(
                    [
                        dmc.Select(
                            label="Choose a person",
                            id="person-select",
                            searchable=True,
                            class_name="select-inpt",
                            zIndex=9999
                        ),
                        dcc.Loading(
                            dcc.Graph(
                                id='most-repeated-words-by-person-graph',
                            ),
                        )
                    ],
                    justify="center",
                    align="center"
                ),
                dbc.Row(
                    [
                        dcc.Loading(
                            dcc.Graph(
                                id='files-by-type-graph',
                            ),
                        )
                    ]
                ),
            ],
            id="graphs-div",
            style={
                'display': 'none'
            }
        )
    ],
    style={
        'margin-bottom': '150px'
    }
)


def create_bar_plot(df, x, y, color, title, x_title, y_title, legend_title, showlegend=True):
    fig = px.bar(
        df,
        x=x,
        y=y,
        title=title,
        color=color,
        # color_discrete_map=color_dict
    )
    fig.update_layout(
        xaxis_title=x_title,
        yaxis_title=y_title,
        legend_title=legend_title,
        showlegend=showlegend
    )

    return fig


@app.callback(
    Output('graphs-div', 'style'),
    Output('n-messages', 'children'),
    Output('n-messages-by-person-graph', 'figure'),
    Output('n-messages-by-month-and-person-graph', 'figure'),
    Output('n-messages-by-year-and-person-graph', 'figure'),
    Output('n-messages-by-hour-and-person-graph', 'figure'),
    Output('n-words', 'children'),
    Output('words-store', 'data'),
    Output('person-select', 'data'),
    Output('person-select', 'value'),
    Output('files-by-type-graph', 'figure'),
    Input('upload-chat', 'contents'),
    State('upload-chat', 'filename'),
    prevent_initial_call=True
)
def upload_chat(file, filename):
    log.info('Uploading chat...')
    chat_name = filename.split(' - ')[1].replace('.zip', '')
    messages = extract_messages_from_chat(file, chat_name)

    chat_df = pd.DataFrame(messages)

    n_messages_by_person_df = chat_df \
        .groupby('person') \
        .agg(n_messages=('person', 'size')) \
        .reset_index() \
        .sort_values('n_messages', ascending=False)

    n_messages_by_person_fig = create_bar_plot(
        n_messages_by_person_df,
        x='person',
        y='n_messages',
        color='person',
        title='Número de mensajes enviados por persona',
        x_title="Persona",
        y_title="Número de mensajes",
        legend_title="Persona",
        showlegend=False
    )

    n_messages_by_month_and_person_df = chat_df \
        .groupby([chat_df.person, chat_df.date.dt.month]) \
        .agg(n_messages=('person', 'size')) \
        .reset_index() \
        .sort_values(['date', 'person'])
    n_messages_by_month_and_person_df['month_name'] = n_messages_by_month_and_person_df['date'] \
        .apply(lambda x: calendar.month_name[x].capitalize())

    n_messages_by_month_and_person_fig = create_bar_plot(
        n_messages_by_month_and_person_df,
        x='month_name',
        y='n_messages',
        color='person',
        title='Número de mensajes enviados por mes por persona',
        x_title="Persona",
        y_title="Número de mensajes",
        legend_title="Persona",
    )

    n_messages_by_year_and_person_df = chat_df \
        .groupby([chat_df.person, chat_df.date.dt.year]) \
        .agg(n_messages=('person', 'size')) \
        .reset_index() \
        .sort_values(['date', 'person'])

    n_messages_by_year_and_person_fig = create_bar_plot(
        n_messages_by_year_and_person_df,
        x='date',
        y='n_messages',
        color='person',
        title='Número de mensajes enviados por año por persona',
        x_title="Persona",
        y_title="Número de mensajes",
        legend_title="Persona",
    )

    n_messages_by_hour_and_person_df = chat_df \
        .groupby([chat_df.person, chat_df.date.dt.hour]) \
        .agg(n_messages=('person', 'size')) \
        .reset_index() \
        .sort_values(['date', 'person'])

    n_messages_by_hour_and_person_fig = create_bar_plot(
        n_messages_by_hour_and_person_df,
        x='date',
        y='n_messages',
        color='person',
        title='Número de mensajes enviados por hora por persona',
        x_title="Persona",
        y_title="Número de mensajes",
        legend_title="Persona",
    )

    aux_df = chat_df \
        .groupby([chat_df.person, chat_df.date.dt.date]) \
        .agg(n_messages=('person', 'size')) \
        .reset_index() \
        .sort_values(['date', 'person'])

    # avg_messages_in_day_by_person_df = aux_df \
    #                                     .groupby('person') \
    #                                     .agg(
    #                                         avg_messages = ('n_messages', 'mean'),
    #                                         max_messages = ('n_messages', 'max'),
    #                                         min_messages = ('n_messages', 'min'),
    #                                     ) \
    #                                     .reset_index() \
    #                                     .sort_values('avg_messages', ascending = False)

    files_df = chat_df[
        (chat_df['message'] == 'audio omitido') |
        (chat_df['message'] == 'sticker omitido') |
        (chat_df['message'] == 'Video omitido') |
        (chat_df['message'] == 'imagen omitida') |
        (chat_df['message'] == 'GIF omitido')
    ][['person', 'message']]

    files_df['file'] = files_df['message'].apply(
        lambda x: x.replace(' omitido', '').replace(' omitida', ''))

    files_by_type_df = files_df \
        .groupby(['person', 'file']) \
        .agg(n_files=('person', 'size')) \
        .reset_index()

    files_by_type_fig = create_bar_plot(
        files_by_type_df,
        x='file',
        y='n_files',
        color='person',
        title='Archivos enviados en la conversación por persona',
        x_title="Tipo de archivo",
        y_title="Número de veces enviado",
        legend_title="Persona",
    )

    person_data = []
    for person in chat_df['person'].unique():
        person_data.append(
            {
                'label': person,
                'value': person,
            }
        )

    person_data.sort(key=lambda x: x['label'])

    words_df = get_words_df(chat_df)

    return None, \
        f'La conversación tiene {chat_df.shape[0]} mensajes enviados.', \
        n_messages_by_person_fig, \
        n_messages_by_month_and_person_fig, \
        n_messages_by_year_and_person_fig, \
        n_messages_by_hour_and_person_fig, \
        f'La conversación tiene {words_df.shape[0]} palabras enviadas quitando stopwords y símbolos.', \
        words_df.to_dict('records'), \
        person_data, \
        person_data[0]['value'], \
        files_by_type_fig


@app.callback(
    Output('most-repeated-words-graph', 'figure'),
    Input('words-store', 'data'),
    prevent_initial_call=True
)
def load_words_graphs(words_records):
    words_df = pd.DataFrame(words_records)

    most_repeated_words_df = words_df \
        .groupby(['word']) \
        .agg(n_times=('word', 'size')) \
        .reset_index() \
        .sort_values('n_times', ascending=False) \
        .head(30)

    most_repeated_words_fig = px.bar(
        most_repeated_words_df,
        x='word',
        y='n_times',
        title='Palabras más repetidas en la conversación',
    )
    most_repeated_words_fig.update_layout(
        xaxis_title="Palabra",
        yaxis_title="Número de veces repetida",
    )

    most_repeated_words_fig.update_xaxes(tickangle=30)

    return most_repeated_words_fig


@app.callback(
    Output('most-repeated-words-by-person-graph', 'figure'),
    Input('person-select', 'value'),
    State('words-store', 'data'),
    prevent_initial_call=True
)
def load_interactive_words_graphs(person, words_records):
    words_df = pd.DataFrame(words_records)

    most_repeated_words_by_person_df = words_df \
        .groupby(['person', 'word']) \
        .agg(n_times=('person', 'size')) \
        .reset_index() \
        .sort_values('n_times', ascending=False)

    print(
        most_repeated_words_by_person_df[most_repeated_words_by_person_df['person'] == 'Luis Zarzoso Rodríguez'].head(30))

    most_repeated_words_by_person_fig = px.bar(
        most_repeated_words_by_person_df[most_repeated_words_by_person_df['person'] == person].sort_values(
            by=['n_times'], ascending=False).head(30),
        x='word',
        y='n_times',
        title=f'Palabras más repetidas en la conversación por {person}',
    )
    most_repeated_words_by_person_fig.update_layout(
        xaxis_title="Palabra",
        yaxis_title="Número de veces repetida",
    )
    most_repeated_words_by_person_fig.update_xaxes(tickangle=30)

    return most_repeated_words_by_person_fig


if __name__ == "__main__":
    app.run_server(debug=True, host="0.0.0.0", port=8080, use_reloader=False)

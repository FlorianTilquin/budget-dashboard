import base64
import io
import dash
from dash import dcc, html, Input, Output, State, callback
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta

# Import custom parser functions
from ofx_parser import parse_ofx, parse_ofc, get_balance_over_time, get_spending_by_category

# Initialize the app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server
app.title = "Personal Budget Dashboard"

# Store for holding parsed data
transaction_dfs = []

# App layout
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H1("Personal Budget Dashboard", className="text-center my-4"),
            html.P("Upload your bank OFX or OFC files to visualize your financial data", 
                  className="text-center text-muted mb-4"),
        ], width=12)
    ]),
    
    # Upload area
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Upload Financial Data"),
                dbc.CardBody([
                    dcc.Upload(
                        id='upload-data',
                        children=html.Div([
                            'Drag and Drop or ',
                            html.A('Select Files')
                        ]),
                        style={
                            'width': '100%',
                            'height': '60px',
                            'lineHeight': '60px',
                            'borderWidth': '1px',
                            'borderStyle': 'dashed',
                            'borderRadius': '5px',
                            'textAlign': 'center',
                            'margin': '10px'
                        },
                        multiple=True
                    ),
                    html.Div(id='upload-output', className="mt-3"),
                    html.Div(id='parsed-files-list', className="mt-3")
                ])
            ], className="mb-4")
        ], width=12)
    ]),
    
    # Time period selector
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Select Time Period"),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Label("Preset Periods:"),
                            dcc.Dropdown(
                                id='time-period-preset',
                                options=[
                                    {'label': 'Last 30 days', 'value': '30D'},
                                    {'label': 'Last 90 days', 'value': '90D'},
                                    {'label': 'Last 6 months', 'value': '6M'},
                                    {'label': 'Last 1 year', 'value': '1Y'},
                                    {'label': 'All time', 'value': 'ALL'},
                                ],
                                value='ALL',
                                clearable=False
                            )
                        ], width=6),
                        dbc.Col([
                            html.Label("Custom Range:"),
                            dcc.DatePickerRange(
                                id='date-picker-range',
                                start_date_placeholder_text="Start Date",
                                end_date_placeholder_text="End Date",
                                calendar_orientation='horizontal',
                                className="w-100"
                            )
                        ], width=6)
                    ])
                ])
            ], className="mb-4")
        ], width=12)
    ]),
    
    # Tabs for different views
    dbc.Row([
        dbc.Col([
            dbc.Tabs([
                dbc.Tab(label="Account Balance", tab_id="tab-balance", children=[
                    dbc.Card([
                        dbc.CardBody([
                            dcc.Graph(id='balance-chart')
                        ])
                    ], className="mt-3")
                ]),
                dbc.Tab(label="Spending Categories", tab_id="tab-categories", children=[
                    dbc.Card([
                        dbc.CardBody([
                            dbc.Row([
                                dbc.Col([
                                    dcc.Graph(id='pie-chart')
                                ], width=6),
                                dbc.Col([
                                    dcc.Graph(id='category-bar-chart')
                                ], width=6)
                            ])
                        ])
                    ], className="mt-3")
                ]),
                dbc.Tab(label="Transactions", tab_id="tab-transactions", children=[
                    dbc.Card([
                        dbc.CardBody([
                            html.Div(id='transactions-table')
                        ])
                    ], className="mt-3")
                ]),
            ], id="tabs", active_tab="tab-balance")
        ], width=12)
    ]),
    
    # Footer
    dbc.Row([
        dbc.Col([
            html.Hr(),
            html.P("Personal Budget Dashboard | Created with Plotly Dash", 
                  className="text-center text-muted")
        ], width=12)
    ], className="mt-4")
    
], fluid=True)

# Callback to parse uploaded files
@app.callback(
    [Output('upload-output', 'children'),
     Output('parsed-files-list', 'children')],
    [Input('upload-data', 'contents')],
    [State('upload-data', 'filename'),
     State('upload-data', 'last_modified')]
)
def update_output(list_of_contents, list_of_names, list_of_dates):
    if list_of_contents is None:
        return html.Div("No files uploaded yet."), html.Div()
    
    global transaction_dfs
    transaction_dfs = []
    
    upload_results = []
    for content, name, date in zip(list_of_contents, list_of_names, list_of_dates):
        try:
            # Decode the content
            content_type, content_string = content.split(',')
            decoded = base64.b64decode(content_string)
            
            # Parse the file based on extension
            if name.endswith('.ofx'):
                df = parse_ofx(decoded, name)
                if not df.empty:
                    transaction_dfs.append(df)
                    upload_results.append(html.Div(f"✅ Successfully parsed {name} - {len(df)} transactions"))
                else:
                    upload_results.append(html.Div(f"❌ Error parsing {name}", style={'color': 'red'}))
            
            elif name.endswith('.ofc'):
                df = parse_ofc(decoded, name)
                if not df.empty:
                    transaction_dfs.append(df)
                    upload_results.append(html.Div(f"✅ Successfully parsed {name} - {len(df)} transactions"))
                else:
                    upload_results.append(html.Div(f"❌ Error parsing {name}", style={'color': 'red'}))
            
            else:
                upload_results.append(html.Div(f"❌ Unsupported file format: {name}", style={'color': 'red'}))
        
        except Exception as e:
            upload_results.append(html.Div(f"❌ Error processing {name}: {str(e)}", style={'color': 'red'}))
    
    # Show list of parsed files
    if transaction_dfs:
        total_transactions = sum(len(df) for df in transaction_dfs)
        file_list = html.Div([
            html.H5(f"Loaded {len(transaction_dfs)} files with {total_transactions} transactions"),
            html.Ul([html.Li(name) for name in list_of_names if name.endswith(('.ofx', '.ofc'))])
        ])
    else:
        file_list = html.Div("No valid files were parsed.")
    
    return html.Div(upload_results), file_list

# Callback to update date picker based on preset
@app.callback(
    Output('date-picker-range', 'start_date'),
    Output('date-picker-range', 'end_date'),
    Input('time-period-preset', 'value')
)
def update_date_picker(preset):
    if not preset or preset == 'ALL':
        return None, None
    
    end_date = datetime.now()
    
    if preset == '30D':
        start_date = end_date - timedelta(days=30)
    elif preset == '90D':
        start_date = end_date - timedelta(days=90)
    elif preset == '6M':
        start_date = end_date - timedelta(days=180)
    elif preset == '1Y':
        start_date = end_date - timedelta(days=365)
    else:
        start_date = None
    
    return start_date.date(), end_date.date()

# Callback to update balance chart
@app.callback(
    Output('balance-chart', 'figure'),
    [Input('parsed-files-list', 'children'),
     Input('date-picker-range', 'start_date'),
     Input('date-picker-range', 'end_date'),
     Input('time-period-preset', 'value')]
)
def update_balance_chart(parsed_files, start_date, end_date, preset):
    global transaction_dfs
    
    if not transaction_dfs:
        return go.Figure().update_layout(
            title="No data available",
            xaxis_title="Date",
            yaxis_title="Balance",
            template="plotly_white"
        )
    
    # Get balance over time
    balance_df = get_balance_over_time(transaction_dfs)
    
    if balance_df.empty:
        return go.Figure().update_layout(
            title="No data available",
            xaxis_title="Date",
            yaxis_title="Balance",
            template="plotly_white"
        )
    
    # Filter based on selected date range
    if start_date and end_date:
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)
        balance_df = balance_df[(balance_df['date'] >= start_date) & (balance_df['date'] <= end_date)]
    
    # Create the figure
    fig = px.line(
        balance_df, 
        x='date', 
        y='balance',
        title="Account Balance Over Time",
        labels={'date': 'Date', 'balance': 'Balance'},
        template="plotly_white"
    )
    
    # Add a horizontal line for zero
    fig.add_hline(y=0, line_dash="dash", line_color="red", opacity=0.7)
    
    # Customize the layout
    fig.update_layout(
        title={
            'text': "Account Balance Over Time",
            'y':0.9,
            'x':0.5,
            'xanchor': 'center',
            'yanchor': 'top'
        },
        xaxis_title="Date",
        yaxis_title="Balance",
        hovermode="x unified"
    )
    
    return fig

# Callback to update pie chart
@app.callback(
    Output('pie-chart', 'figure'),
    [Input('parsed-files-list', 'children'),
     Input('date-picker-range', 'start_date'),
     Input('date-picker-range', 'end_date')]
)
def update_pie_chart(parsed_files, start_date, end_date):
    global transaction_dfs
    
    if not transaction_dfs:
        return go.Figure().update_layout(
            title="No data available",
            template="plotly_white"
        )
    
    # Filter by date if needed
    filtered_dfs = transaction_dfs
    if start_date and end_date:
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)
        filtered_dfs = [
            df[
                (df['date'] >= start_date) & 
                (df['date'] <= end_date)
            ] 
            for df in transaction_dfs
        ]
    
    # Get spending by category
    category_spending = get_spending_by_category(filtered_dfs)
    
    if category_spending.empty:
        return go.Figure().update_layout(
            title="No expense data available",
            template="plotly_white"
        )
    
    # Create the pie chart
    fig = px.pie(
        category_spending, 
        values='amount', 
        names='category',
        title="Spending by Category",
        template="plotly_white",
        hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    
    # Customize the layout
    fig.update_layout(
        title={
            'text': "Spending by Category",
            'y':0.9,
            'x':0.5,
            'xanchor': 'center',
            'yanchor': 'top'
        },
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.2,
            xanchor="center",
            x=0.5
        )
    )
    
    return fig

# Callback to update category bar chart
@app.callback(
    Output('category-bar-chart', 'figure'),
    [Input('parsed-files-list', 'children'),
     Input('date-picker-range', 'start_date'),
     Input('date-picker-range', 'end_date')]
)
def update_category_bar_chart(parsed_files, start_date, end_date):
    global transaction_dfs
    
    if not transaction_dfs:
        return go.Figure().update_layout(
            title="No data available",
            template="plotly_white"
        )
    
    # Filter by date if needed
    filtered_dfs = transaction_dfs
    if start_date and end_date:
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)
        filtered_dfs = [
            df[
                (df['date'] >= start_date) & 
                (df['date'] <= end_date)
            ] 
            for df in transaction_dfs
        ]
    
    # Get spending by category
    category_spending = get_spending_by_category(filtered_dfs)
    
    if category_spending.empty:
        return go.Figure().update_layout(
            title="No expense data available",
            template="plotly_white"
        )
    
    # Create the bar chart
    fig = px.bar(
        category_spending, 
        y='category', 
        x='amount',
        title="Spending by Category",
        labels={'amount': 'Amount Spent', 'category': 'Category'},
        template="plotly_white",
        orientation='h',
        color='amount',
        color_continuous_scale=px.colors.sequential.Viridis
    )
    
    # Customize the layout
    fig.update_layout(
        title={
            'text': "Spending by Category",
            'y':0.9,
            'x':0.5,
            'xanchor': 'center',
            'yanchor': 'top'
        },
        yaxis={'categoryorder':'total ascending'}
    )
    
    return fig

# Callback to update transactions table
@app.callback(
    Output('transactions-table', 'children'),
    [Input('parsed-files-list', 'children'),
     Input('date-picker-range', 'start_date'),
     Input('date-picker-range', 'end_date')]
)
def update_transactions_table(parsed_files, start_date, end_date):
    global transaction_dfs
    
    if not transaction_dfs:
        return html.Div("No transaction data available")
    
    # Combine all dataframes
    combined_df = pd.concat(transaction_dfs, ignore_index=True)
    
    if combined_df.empty:
        return html.Div("No transaction data available")
    
    # Filter by date if needed
    if start_date and end_date:
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)
        combined_df = combined_df[(combined_df['date'] >= start_date) & (combined_df['date'] <= end_date)]
    
    # Sort by date
    combined_df = combined_df.sort_values('date', ascending=False)
    
    # Format the date and amount columns
    combined_df['date'] = combined_df['date'].dt.strftime('%Y-%m-%d')
    combined_df['amount'] = combined_df['amount'].apply(lambda x: f"{x:.2f}")
    
    # Select only the columns we want to display
    display_df = combined_df[['date', 'amount', 'description', 'category']]
    
    # Create a table with the transactions
    table = dbc.Table.from_dataframe(
        display_df, 
        striped=True, 
        bordered=True, 
        hover=True,
        responsive=True
    )
    
    return table

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True) 
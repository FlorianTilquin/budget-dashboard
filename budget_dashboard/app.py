import base64
import io
import dash
from dash import dcc, html, Input, Output, State, callback
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
import uuid
import os
from tempfile import gettempdir

# Import custom parser functions
from budget_dashboard.parsers.ofx_parser import parse_ofx, parse_ofc, get_balance_over_time, get_spending_by_category
from budget_dashboard.parsers.ofx_parser import save_transactions_to_parquet, load_transactions_from_parquet

# Import the categories from ofx_parser
from budget_dashboard.parsers.ofx_parser import categorize_transaction

# Initialize the app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server
app.title = "Personal Budget Dashboard"

# Store for holding parsed data
transaction_dfs = []

# Helper function to get all available categories
def get_available_categories():
    # This list should match the categories in categorize_transaction
    categories = [
        'Courses', 'Restaurants', 'Transport', 'Shopping', 'Seconde Main', 
        'Loisirs', 'Sante', 'Services', 'Logement', 'Revenus', 
        'Virements', 'Voiture', 'Banque', 'Maison', 'Autre'
    ]
    return sorted(categories)

# App layout
app.layout = dbc.Container([
    # Add store component to the main layout
    dcc.Store(id='transaction-data-store'),
    
    dbc.Row([
        dbc.Col([
            html.H1("Personal Budget Dashboard", className="text-center my-4"),
            html.P("Upload your bank OFX or OFC files to visualize your financial data", 
                  className="text-center text-muted mb-4"),
        ], width=12)
    ]),
    
    # Account Balance Input
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Account Information"),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Label("Current Account Balance (€):"),
                            dbc.Input(
                                id='manual-balance-input',
                                type='number',
                                placeholder='Enter your current account balance',
                                step=0.01,
                                value=0,
                            ),
                            html.Small("Enter your most recent account balance in euros", className="text-muted")
                        ], width=12)
                    ])
                ])
            ], className="mb-4")
        ], width=12)
    ]),
    
    # Upload area
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Upload Financial Data"),
                dbc.CardBody([
                    html.H5("Import Data", className="card-title"),
                    dbc.Tabs([
                        dbc.Tab(label="Bank Files (OFX/OFC)", children=[
                            dcc.Upload(
                                id='upload-data',
                                children=html.Div([
                                    'Drag and Drop or ',
                                    html.A('Select OFX/OFC Files')
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
                                multiple=True,
                                accept='.ofx,.ofc'
                            ),
                        ]),
                        dbc.Tab(label="Parquet Files", children=[
                            dcc.Upload(
                                id='upload-parquet',
                                children=html.Div([
                                    'Drag and Drop or ',
                                    html.A('Select Parquet Files')
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
                                multiple=True,
                                accept='.parquet'
                            ),
                        ]),
                    ]),
                    html.Div(id='upload-output', className="mt-3"),
                    html.Div(id='parsed-files-list', className="mt-3"),
                    html.Hr(),
                    html.H5("Export Data", className="card-title mt-3"),
                    dbc.Button(
                        "Save Transactions as Parquet",
                        id="save-parquet-button",
                        color="success",
                        className="me-2"
                    ),
                    html.Div(id='save-parquet-output', className="mt-3")
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
                            # Add refresh button in the main layout
                            html.Div([
                                dbc.Button(
                                    "Actualiser les graphiques",
                                    id="refresh-button",
                                    color="primary",
                                    className="mb-3"
                                ),
                                html.P("Pour modifier la catégorie d'une transaction, sélectionnez-la dans le menu déroulant et cliquez sur le bouton ci-dessus.", 
                                      className="text-muted mb-3")
                            ]),
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
    [Output('upload-output', 'children', allow_duplicate=True),
     Output('parsed-files-list', 'children', allow_duplicate=True)],
    [Input('upload-data', 'contents')],
    [State('upload-data', 'filename'),
     State('upload-data', 'last_modified')],
    prevent_initial_call=True
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

# Callback to parse uploaded parquet files
@app.callback(
    [Output('upload-output', 'children', allow_duplicate=True),
     Output('parsed-files-list', 'children', allow_duplicate=True)],
    [Input('upload-parquet', 'contents')],
    [State('upload-parquet', 'filename'),
     State('upload-parquet', 'last_modified')],
    prevent_initial_call=True
)
def update_output_parquet(list_of_contents, list_of_names, list_of_dates):
    if list_of_contents is None:
        return html.Div("No files uploaded yet."), html.Div()
    
    global transaction_dfs
    
    upload_results = []
    new_dfs = []
    
    for content, name, date in zip(list_of_contents, list_of_names, list_of_dates):
        try:
            # Decode the content
            content_type, content_string = content.split(',')
            decoded = base64.b64decode(content_string)
            
            # Parse the file
            if name.endswith('.parquet'):
                df = load_transactions_from_parquet(decoded, name)
                if not df.empty:
                    new_dfs.append(df)
                    upload_results.append(html.Div(f"✅ Successfully loaded {name} - {len(df)} transactions"))
                else:
                    upload_results.append(html.Div(f"❌ Error loading {name}", style={'color': 'red'}))
            else:
                upload_results.append(html.Div(f"❌ Unsupported file format: {name}", style={'color': 'red'}))
        
        except Exception as e:
            upload_results.append(html.Div(f"❌ Error processing {name}: {str(e)}", style={'color': 'red'}))
    
    # Add new dataframes to existing ones
    transaction_dfs.extend(new_dfs)
    
    # Show list of parsed files
    if new_dfs:
        total_transactions = sum(len(df) for df in new_dfs)
        file_list = html.Div([
            html.H5(f"Loaded {len(new_dfs)} parquet files with {total_transactions} transactions"),
            html.Ul([html.Li(name) for name in list_of_names if name.endswith('.parquet')])
        ])
    else:
        file_list = html.Div("No valid parquet files were loaded.")
    
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
     Input('time-period-preset', 'value'),
     Input('manual-balance-input', 'value')]
)
def update_balance_chart(parsed_files, start_date, end_date, preset, manual_balance):
    global transaction_dfs
    
    if not transaction_dfs:
        return go.Figure().update_layout(
            title="No data available",
            xaxis_title="Date",
            yaxis_title="Balance (€)",
            template="plotly_white"
        )
    
    # Get balance over time - using the manually entered balance if available
    manual_balance = 0 if manual_balance is None else float(manual_balance)
    balance_df = get_balance_over_time(transaction_dfs, manual_balance)
    
    if balance_df.empty:
        return go.Figure().update_layout(
            title="No data available",
            xaxis_title="Date",
            yaxis_title="Balance (€)",
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
        labels={'date': 'Date', 'balance': 'Balance (€)'},
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
        yaxis_title="Balance (€)",
        hovermode="x unified"
    )
    
    # Format y-axis tick values with euro symbol
    fig.update_layout(
        yaxis=dict(
            tickprefix="€",
            tickformat=",."
        )
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
    
    # Add euro symbol to hover data
    fig.update_traces(
        hovertemplate='<b>%{label}</b><br>Amount: €%{value:.2f}<br>Percentage: %{percent}'
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
        labels={'amount': 'Amount Spent (€)', 'category': 'Category'},
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
        yaxis={'categoryorder':'total ascending'},
        xaxis=dict(
            tickprefix="€",
            tickformat=",."
        )
    )
    
    # Add Euro symbol to hover data
    fig.update_traces(
        hovertemplate='<b>%{y}</b><br>€%{x:.2f}'
    )
    
    return fig

# Callback to update transactions table
@app.callback(
    [Output('transactions-table', 'children'),
     Output('transaction-data-store', 'data')],
    [Input('parsed-files-list', 'children'),
     Input('date-picker-range', 'start_date'),
     Input('date-picker-range', 'end_date')]
)
def update_transactions_table(parsed_files, start_date, end_date):
    global transaction_dfs
    
    if not transaction_dfs:
        return html.Div("No transaction data available"), []
    
    # Combine all dataframes
    combined_df = pd.concat(transaction_dfs, ignore_index=True)
    
    if combined_df.empty:
        return html.Div("No transaction data available"), []
    
    # Filter by date if needed
    if start_date and end_date:
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)
        combined_df = combined_df[(combined_df['date'] >= start_date) & (combined_df['date'] <= end_date)]
    
    # Sort by date
    combined_df = combined_df.sort_values('date', ascending=False)
    
    # Format the date column
    combined_df['date'] = combined_df['date'].dt.strftime('%Y-%m-%d')
    
    # Add a unique ID for each transaction for callbacks
    combined_df['id'] = [str(uuid.uuid4()) for _ in range(len(combined_df))]
    
    # Get all available categories
    categories = get_available_categories()
    
    # Create a custom table with dropdown menus for categories
    table_header = [
        html.Thead(html.Tr([
            html.Th("Date"), 
            html.Th("Montant"), 
            html.Th("Description"), 
            html.Th("Catégorie")
        ]))
    ]
    
    rows = []
    for i, row in combined_df.iterrows():
        # Format amount with euro symbol
        amount = f"€{float(row['amount']):.2f}" if isinstance(row['amount'], (int, float)) else row['amount']
        
        # Create a dropdown for the category with the current value selected
        category_dropdown = dcc.Dropdown(
            id={'type': 'category-dropdown', 'index': row['id']},
            options=[{'label': cat, 'value': cat} for cat in categories],
            value=row['category'],
            clearable=False,
            style={'width': '100%'}
        )
        
        # Create a table row with the transaction data
        tr = html.Tr([
            html.Td(row['date']),
            html.Td(amount),
            html.Td(row['description']),
            html.Td(category_dropdown)
        ])
        rows.append(tr)
    
    table_body = [html.Tbody(rows)]
    
    # Create the table
    table = dbc.Table(
        table_header + table_body,
        striped=True,
        bordered=True,
        hover=True,
        responsive=True
    )
    
    # Return both the table and the data for the store
    return table, combined_df.to_dict('records')

# Callback to update transaction category
@app.callback(
    Output('transaction-data-store', 'data', allow_duplicate=True),
    [Input({'type': 'category-dropdown', 'index': dash.dependencies.ALL}, 'value')],
    [State('transaction-data-store', 'data')],
    prevent_initial_call=True  # Add this to prevent the callback from firing on initial load
)
def update_transaction_category(new_categories, data):
    # If there's no data, return
    if not data or not new_categories:
        return data
    
    # Create a context to know which dropdown triggered the callback
    ctx = dash.callback_context
    
    # If the callback wasn't triggered by a dropdown, return
    if not ctx.triggered:
        return data
    
    # Get the ID of the dropdown that triggered the callback
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    # Parse the JSON string to get the index
    try:
        trigger_dict = eval(trigger_id)
        transaction_id = trigger_dict['index']
        
        # Find the transaction in the data and update its category
        for transaction in data:
            if transaction['id'] == transaction_id:
                # Find the index of the new category in the list of values
                dropdown_index = [d['index'] for d in dash.callback_context.inputs_list[0]['id']]
                new_category_index = dropdown_index.index(transaction_id)
                
                # Update the category
                transaction['category'] = new_categories[new_category_index]
                
                # Also update the corresponding transaction in transaction_dfs
                update_transaction_category_in_dfs(transaction_id, transaction['category'])
                
                break
    except:
        # If there's an error parsing the ID or finding the transaction,
        # just return the unchanged data
        pass
    
    return data

def update_transaction_category_in_dfs(transaction_id, new_category):
    """
    Update the category of a transaction in the global transaction_dfs.
    
    Args:
        transaction_id (str): The ID of the transaction to update
        new_category (str): The new category value
    """
    global transaction_dfs
    
    # Iterate through each DataFrame in transaction_dfs
    for i, df in enumerate(transaction_dfs):
        # Check if the DataFrame has an 'id' column
        if 'id' not in df.columns:
            # Add an 'id' column if it doesn't exist
            df['id'] = [str(uuid.uuid4()) for _ in range(len(df))]
            transaction_dfs[i] = df
        
        # Try to find the transaction and update its category
        if transaction_id in df['id'].values:
            transaction_dfs[i].loc[df['id'] == transaction_id, 'category'] = new_category
            break

# Add a refresh callbacks to update the charts
@app.callback(
    [Output('pie-chart', 'figure', allow_duplicate=True),
     Output('category-bar-chart', 'figure', allow_duplicate=True)],
    [Input('refresh-button', 'n_clicks'),
     Input('parsed-files-list', 'children'),
     Input('date-picker-range', 'start_date'),
     Input('date-picker-range', 'end_date')],
    prevent_initial_call=True  # Add this to prevent the callback from firing on initial load
)
def refresh_charts(n_clicks, parsed_files, start_date, end_date):
    # Just trigger both existing callbacks by returning their outputs
    pie_chart = update_pie_chart(parsed_files, start_date, end_date)
    bar_chart = update_category_bar_chart(parsed_files, start_date, end_date)
    return pie_chart, bar_chart

# Callback to save transactions to parquet
@app.callback(
    Output('save-parquet-output', 'children'),
    [Input('save-parquet-button', 'n_clicks')],
    prevent_initial_call=True
)
def save_transactions(n_clicks):
    global transaction_dfs
    
    if not transaction_dfs:
        return html.Div("No transactions to save.", style={'color': 'red'})
    
    try:
        # Create a filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"transactions_{timestamp}.parquet"
        
        # Save to app directory
        app_dir = os.path.dirname(os.path.abspath(__file__))
        filepath = os.path.join(app_dir, filename)
        
        # Save the transactions
        success = save_transactions_to_parquet(transaction_dfs, filepath)
        
        if success:
            return html.Div([
                html.P(f"✅ Successfully saved transactions to:", className="mb-0"),
                html.Code(filepath, className="ms-2"),
                html.P("You can reload this file later using the Parquet Files tab.", className="mt-2 text-muted small")
            ], className="text-success")
        else:
            return html.Div("❌ Failed to save transactions.", style={'color': 'red'})
    
    except Exception as e:
        return html.Div(f"❌ Error saving transactions: {str(e)}", style={'color': 'red'})

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True) 
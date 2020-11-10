from flask import Flask, render_template
from flask_restful import Resource
import pandas as pd
from panel import layout
from param import Event
import plotly.graph_objs as go
import panel as pn
import datetime as dt

from bokeh.embed import server_document
from bokeh.server.server import Server
from tornado.ioloop import IOLoop

from CalculateIntegrity.getIntegrityValue import integrityValue

pn.extension()

filename = 'data/data.csv'
# check file extension and access the data accordingly
if filename.endswith('.xlsx'):
    df = pd.read_excel(filename)
elif filename.endswith('.csv'):
    df = pd.read_csv(filename, sep=';')
    if len(df.columns) == 1:
        df = pd.read_csv(filename)

# convert string to datetime format
df['startdatum'] = pd.to_datetime(pd.to_datetime(df['startdatum']).dt.strftime('%Y-%m-%d'), format='%Y-%m-%d')
df = df.sort_values(by="startdatum")

# collect all the column names whose values are either int or float
flow_columns = []

for i in df.columns:
    if df[i].dtypes == 'int64' or df[i].dtypes == 'float64':
        flow_columns.append(i)

selectIntegrity = pn.widgets.IntSlider(name='Integrity value', start=0, end=50, value=0)
selectStartDate = pn.widgets.DateSlider(name='Start Date', start=df['startdatum'].min(), end=df['startdatum'].max(), value=df['startdatum'].min())
selectEndDate = pn.widgets.DateSlider(name='End Date', start=df['startdatum'].min(), end=df['startdatum'].max(), value=df['startdatum'].max())
selectInflow = pn.widgets.MultiChoice(name='Value for Y-axis', options=flow_columns, value=[flow_columns[0]])
selectBrand = pn.widgets.MultiChoice(name='Brand', options=list(df['brand'].unique()), value=[df['brand'][0]])
selectPackage = pn.widgets.MultiChoice(name='Package', options=list(df['package'].unique()), value=[df['package'][0]])
selectType = pn.widgets.MultiChoice(name='Type', options=list(df['type'].unique()), value=[df['type'][0]])
buttonValue = True
button = pn.widgets.Button(name='SwitchView', button_type='primary', width=250)

title = 'PANEL - SUBSCRIBER - INFLOW/OUTFLOW'
title2 = '<H4> Visualising forecasting </H4>'
titleIntegrity = '<H6> Promotion Integrity Value: </H6>'
titleDate = '<h6> Select start and end date: </h6>'
titleBrand = '<h6> Pick one or more option(s) from the dropdown below: </h6>'
titleInflow = '<h6> Pick any flow type from the dropdown below: </h6>'

bootstrap = pn.template.BootstrapTemplate(title=title)

# add forecasted value
import numpy as np
#df['forecasted'] = np.random.choice([0,1], df.shape[0])
df['forecasted'] = np.where(df['startdatum'].dt.year < 2020, 0, 1)

table_df = pd.DataFrame()

@pn.depends(selectedIntValue=selectIntegrity, selectedStartDate=selectStartDate, selectedEndDate=selectEndDate, selectedBrand=selectBrand, selectedPackage=selectPackage, selectedType=selectType, selectedInflow=selectInflow)
def plotGraph(selectedIntValue, selectedStartDate, selectedEndDate, selectedBrand, selectedPackage, selectedType, selectedInflow):
    global table_df
    # select all combinations of input
    traces = []
    table_df = pd.DataFrame()
    for brand, package, ptype, inflowt in [(brand, package, ptype, inflowt) for brand in selectedBrand for package in selectedPackage for ptype in selectedType for inflowt in selectedInflow]:
        df_sub = df
        if brand:
            df_sub = df_sub[df_sub['brand'] == brand]
        if package:
            df_sub = df_sub[df_sub['package'] == package]
        if ptype:
            df_sub = df_sub[df_sub['type'] == ptype]
            
        if selectedStartDate < selectedEndDate:
            df_sub = df_sub[df_sub['startdatum'] >= selectedStartDate]
            df_sub = df_sub[df_sub['startdatum'] <= selectedEndDate]

        df_sub1 = df_sub[df_sub.forecasted == 1]
        df_sub0 = df_sub[df_sub.forecasted == 0]
            
        if selectedIntValue:
            df_sub1[inflowt] = df_sub1[inflowt].add(integrityValue(selectedIntValue)) 

        df_sub['startdatum'] = df_sub['startdatum'].dt.strftime("%Y-%m-%d")

        table_df = pd.concat([table_df, df_sub], axis=0)

        traces.append(go.Scatter(x=df_sub0.startdatum, y=df_sub0[inflowt], mode='lines', name=brand+'-'+package+'-'+ptype+'-'+inflowt+'-forecasted=0'))
        traces.append(go.Scatter(x=df_sub1.startdatum, y=df_sub1[inflowt], mode='lines+markers', marker=dict(size=5), name=brand+'-'+package+'-'+ptype+'-'+inflowt+'-forecasted=1'))
    
    for i in flow_columns:
        if i not in selectedInflow:
            del table_df[i]

    layout = go.Layout(
        showlegend=True, 
        width=1200, 
        height=600,
        autosize=False,
        xaxis=dict(title='Date'),
        yaxis=dict( title='Inflow/Outflow')
    ) 

    if buttonValue:
        return go.Figure(data=traces, layout=layout)
    else:
        return addFigure()

def createTable():
    colName = []
    for i in table_df.columns:
        if i.find('_'):
            splVal = i.split('_')
            val = '<b>'
            for j in splVal:
                val = val+j.capitalize()+'<br>'
            val += '</b>'
            colName.append(val)

    data = go.Table(
        columnwidth=[1,1],
        header=dict(
                values=colName,
                line_color='darkslategray',
                fill_color='lightskyblue',
                font_size=12,
                height=30,
                align=['center', 'center'],
        ), 
        cells=dict(values= [table_df[val] for val in table_df.columns],
                line_color='darkslategray',
                fill_color='lightcyan',
                font_size=12,
                height=30
        )
    )
    layout = go.Layout(
        width=1200, 
        height=600,
    )
    return go.Figure(data=data, layout=layout)

def addFigure():
    if buttonValue:
        try:
            bootstrap.main[0][2].pop(1)
        except:
            pass
        finally:
            bootstrap.main[0][2].append(
                pn.Card(plotGraph)
            )
    else:
        try:
            bootstrap.main[0][2].pop(1)
        except:
            pass
        finally:
            bootstrap.main[0][2].append(
                pn.Card(createTable)
            )

def changeButtonValue(event):
    global buttonValue
    buttonValue = not buttonValue

    addFigure()

button.on_click(changeButtonValue)

pn.config.sizing_mode = 'stretch_width'

bootstrap.main.append(
    pn.Column(
        pn.Column(
            title2,
        ),
        pn.Row(
            pn.Column(
                titleIntegrity,
                selectIntegrity,
                titleDate,
                selectStartDate,
                selectEndDate
            ),
            pn.Column(
                titleBrand,
                selectBrand,
                selectPackage,
                selectType
            ),
            pn.Column(
                titleInflow,
                selectInflow
            )
        ),
        pn.Column(
            button
        )
    )
)

addFigure()
bootstrap.show(host='localhost', port=8000)
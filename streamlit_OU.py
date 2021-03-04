import streamlit as st
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import altair as alt

from PIL import Image
image = Image.open('logo.png')


st.image(image,use_column_width=True)
st.title('2021 - NHL Wager Talk')

# Load data 
data_load_state = st.text('Loading data...')

data = pd.read_csv('nhl_bet.csv')
# Notify the reader that the data was successfully loaded.
data_load_state.text('Loading data...done!')


if st.button('Hide Raw Data'):
    st.write('Data Table Hidden')
else:
    st.subheader('Raw data')
    st.dataframe(data.style.highlight_max(axis=0))

st.subheader('Select Parameters')

#Filtering For Days of Rest
Days_to_filter = st.slider('Days of Rest', 0, max(data.Date_diff), 3)
st.text('Number of Days Rest %s' % Days_to_filter)
filtered_data = data[data['Date_diff'] == Days_to_filter]



#Filtering For Home and Away
home_away = st.selectbox("Is the Team Home or Away?",
                 ('Home', 'Away'))
st.write('You selected', home_away)

#Filtering For Distance
Distance_to_filter = st.slider('Distance From Home', 0.0, max(data.Distance), (0.0, 500.0))
st.text('Distance From Home %s' % Distance_to_filter[0])
filtered_data = filtered_data[(filtered_data['Distance'] >= Distance_to_filter[0]) & (filtered_data['Distance'] <= Distance_to_filter[1])]


#st.subheader('Selected # of Days on Home Stand')

#st.subheader('Selected # of Days on Road Trip')


st.subheader('Over/Under Results')

c = alt.Chart(filtered_data).mark_bar().encode(
    x='OUr', y='count()', color='OUr', tooltip ='count()')

st.altair_chart(c, use_container_width=True)
#if genre == 'Comedy':
#    st.write('You selected comedy.')
#else:
#    st.write("You didn't select comedy.")

import plotly.express as px

fig = px.histogram(data, x="Date_diff", color='OUr',
                   barmode='group', template='plotly_white')
st.plotly_chart(fig, use_container_width=True)


st.subheader('Home Stand O/U Results')
fig1 = px.histogram(data[data["Home_Stand"]>0], x="Home_Stand", color='OUr',
                    barmode='group', template='plotly_white')
st.plotly_chart(fig1, use_container_width=True)

st.subheader('Road Trip O/U Results')
fig2 = px.histogram(data[data["Road_Trip"]>0], x="Road_Trip", color='OUr',
                    barmode='group', template='plotly_white')
st.plotly_chart(fig2, use_container_width=True)




#Filter for OU Line
Line_to_filter = st.slider('O/U Line', 0.0, max(data.Total), (0.0, 5.5))
filtered_data2 = filtered_data[(data['Total'] >= Line_to_filter[0]) &
                              (data['Total'] <= Line_to_filter[1])]


st.subheader('O/U Totals')
fig3 = px.histogram(data, x="Total", color='OUr',
                    barmode='group', template='plotly_white')
st.plotly_chart(fig3, use_container_width=True)

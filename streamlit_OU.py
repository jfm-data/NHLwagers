import streamlit as st
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import altair as alt
from requests import get
import re
import os
from bs4 import BeautifulSoup
from urllib.request import Request, urlopen
import datetime
import time
import matplotlib.pyplot as plt
import statsmodels.api as sm
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
geolocator = Nominatim(user_agent='myuseragent')
import lxml
import plotly.express as px

from PIL import Image


#with open("styles/style.css") as f:
#    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

st.set_page_config(
    page_title="O/U Hockey Analytics",
    page_icon=":ice_hockey_stick_and_puck:"
)
h_col1, h_col2 = st.beta_columns([7,6])
#Dummy data to get the header to display correctly
st.markdown("""<Head>
            <Title> Test Title</Title><link rel="shortcut icon" href="favicon.ico" type="image/x-icon"> </Head>""",unsafe_allow_html=True)


logo_image = Image.open(f'NHLimages/mayflower.jpg') 
#Title/Header
with h_col1:
    st.markdown("""<h1 style="text-align:center;color:white;font-weight:bolder;font-size:70px;font-family:helvetica; background:
                -webkit-linear-gradient(#a73305,#000000,#093ff0); -webkit-background-clip:
                text;-webkit-text-fill-color: transparent;">NHL<br>Wager<br>Analytics</h1>""",unsafe_allow_html=True)

with h_col2:
    st.image(logo_image)


# Load data 
data_load_state = st.text('Checking and Fetching Data...')

#####################################
#### Data Gathering and Cleaning ####
#####################################

master_df = pd.read_csv('master_df.csv')
start = pd.to_datetime(master_df.Date[-1:]).dt.date.values[0]+datetime.timedelta(days=1)
today = datetime.date.today()
yesterday = today-datetime.timedelta(days = 1) 

#Function to covert dates to string
def covert_dates(date1, date2):
    covert_list = []
    days = pd.date_range(date1, date2, freq='d')
    for i in range(len(days)):
        covert_list.append(int(days[i].strftime('%Y%m%d')))
    return covert_list

#Function to fetch missing data
@st.cache
def get_data(date1, date2):
    new_df = pd.DataFrame()
    for day in covert_dates(date1, date2):
            site = f"https://sportsdatabase.com/nhl/query?output=default&sdql=date%3D{day}&submit=++S+D+Q+L+%21++"
            hdr = {'User-Agent': 'Mozilla/5.0'}
            req = Request(site, headers=hdr)
            page = urlopen(req)
            soup = BeautifulSoup(page)
            tables = soup.find('table', attrs={'id':'DT_Table'})
            page_df = pd.read_html(str(tables))[0]
            new_df = pd.concat([new_df, page_df])
            time.sleep(1)
    return new_df

#Check if the data needs updating
if start <= yesterday:
    new_data = get_data(start, today)
    master_df = pd.concat([master_df, new_data])
    
#Save updated data as csv    
#master_df.to_csv("master_df.csv", index=False)
    
raw_data = pd.read_csv('master_df.csv')


def clean_data(df):
    df.Date =pd.to_datetime(df.Date)
    df= df.sort_values(by=['Team', 'Date']).reset_index()
    df.insert(2, "Date_Prev", df.Date.shift(1))
    df.insert(2, "Days_Rest", (df.Date_Prev-df.Date)*-1)
    df = df.drop(['index','Season', 'P1', 'P2', 'P3'], axis=1)
    return df

#Fucntion to identify a team change to break streak counts

def trips(home_or_away, TeamChange, Site):
     list =[]
     x = 0
     for i, j in zip(TeamChange, Site):
         if i == False:
             x = x
         else:
             x = 0
         if j == home_or_away:
             x += 1
         else:
             x = 0
         list.append(x)
     return list

#Function to calculate the distance the road team is from home

def distance_calc(df):
    df.insert(4,"Team_City", df.Team.map(team_dict['City']))
    df.insert(6,"Opp_City", df.Opp.map(team_dict['City']))
    df.insert(9,"Team_point", df.Team.map(team_dict['Citypoint']))
    df.insert(10,"Opp_point", df.Opp.map(team_dict['Citypoint']))
    df['Distance'] = df.apply(lambda x: geodesic(x['Team_point'],x['Opp_point']).km, axis=1)
    df['Team_distance'] = df.apply(lambda x: 0 if x.Site == "home" else x.Distance, axis=1)
    df['Opp_distance'] = df.apply(lambda x: 0 if x.Site == "away" else x.Distance, axis=1)
    df = df.drop(['Team_point','Distance','Opp_point'], axis=1)
    return df

#Function to count the current streak of home or games 

def road_trips(df):
    df.insert(4, "TeamChange", df["Team"].shift(1, fill_value=df["Team"].head(1)) != df["Team"])
    df.insert(10, "Home_Stand", trips("home", df.TeamChange, df.Site))
    df.insert(11, "Road_Trip", trips("away", df.TeamChange, df.Site))
    df.Days_Rest = df.Days_Rest.dt.days
    df.Days_Rest = df.Days_Rest.fillna(5)
    df.Days_Rest = df.Days_Rest.astype(int)-1
    df.loc[df.Days_Rest < 0, 'Days_Rest'] = 5
    df = df.drop('TeamChange', axis=1)
    return df

#Function to pair games into a singel record -- for O/U analysis
def opp_func (df):
    df.insert(2,"Opp_Days_Rest", eda_df.Oppkey.map(opp_days_rest))
    df.insert(10,"Opp_home_stand", eda_df.Oppkey.map(opp_home_stand))
    df.insert(11,"Opp_road_trip", eda_df.Oppkey.map(opp_road_trip))
    return df

#Func to calculate the unit return of each game and team
def unit_value(Line, Result):
    if Line < 0 and Result == 'W':
        return 1
    elif Line < 0 and Result == 'L':
        return Line/100
    elif Line > 0 and Result == 'W':
        return Line/100
    elif Line > 0 and Result == 'L':
        return -1
    
nhltable= pd.read_csv('nhltable.csv')
team_dict = nhltable.set_index('Team').to_dict()

eda_df = clean_data(master_df)
eda_df = distance_calc(eda_df)
eda_df = road_trips(eda_df)

#Create keys for pairing
Teamkey = []
Oppkey = []
for i in range(len(eda_df.Date)):
            Teamkey.append(str(covert_dates(eda_df.Date[i], eda_df.Date[i])[0])+eda_df.Team[i])
            Oppkey.append(str(covert_dates(eda_df.Date[i], eda_df.Date[i])[0])+eda_df.Opp[i])
eda_df['Oppkey'] = Oppkey

opp_days_rest = dict(zip(Teamkey, eda_df.Days_Rest))
opp_home_stand = dict(zip(Teamkey, eda_df.Home_Stand))
opp_road_trip = dict(zip(Teamkey, eda_df.Road_Trip))
opp_func(eda_df)

eda_df.Final = eda_df.Final.fillna('0-0')
eda_df = eda_df.fillna(0)

eda_df = pd.concat([eda_df, pd.get_dummies(eda_df.OUr)], axis=1)

goals_df = eda_df['Final'].str.split('-', expand=True).rename(columns={0:'Team_Goals', 1:'Opp_Goals'}).astype(int)

eda_df = pd.concat([eda_df, goals_df], axis=1)
eda_df['total_O'] = eda_df.groupby('Team')['O'].cumsum()
eda_df['total_U'] = eda_df.groupby('Team')['U'].cumsum()
eda_df['total_P'] = eda_df.groupby('Team')['P'].cumsum()
eda_df['total_Team_goals'] = eda_df.groupby('Team')['Team_Goals'].cumsum()
eda_df['total_Opp_goals'] = eda_df.groupby('Team')['Opp_Goals'].cumsum()
#eda_df = eda_df.loc[eda_df['OUr']!='P']
#eda_df['y'] = (eda_df.OUr=='O').astype(int)

eda_df['Team_U'] = eda_df.groupby('Team')['total_U'].transform('max')
eda_df['Team_O'] = eda_df.groupby('Team')['total_O'].transform('max')
eda_df['Opp_U'] = eda_df.groupby('Opp')['total_U'].transform('max')
eda_df['Opp_O'] = eda_df.groupby('Opp')['total_O'].transform('max')
eda_df['Team_Goals_Scored'] = eda_df.groupby('Team')['total_Team_goals'].transform('max')
eda_df['Team_Goals_Allowed'] = eda_df.groupby('Team')['total_Opp_goals'].transform('max')
eda_df['Opp_Goals_Scored'] = eda_df.groupby('Opp')['total_Team_goals'].transform('max')
eda_df['Opp_Goals_Allowed'] = eda_df.groupby('Opp')['total_Opp_goals'].transform('max')

#eda_df['Units'] = eda_df.apply(lambda x: unit_value(x.Line, x.SUr), axis=1)

#Tonight's games data
today_np = np.datetime64(today)
tonight_df= eda_df[['Team','Opp','Total','Home_Stand','Opp_road_trip','Days_Rest','Opp_Days_Rest', 'Opp_distance', 'Team_U',
                   'Opp_U','Team_O', 'Opp_O','Team_Goals_Scored', 'Opp_Goals_Scored','Team_Goals_Allowed', 'Opp_Goals_Allowed', "Date",'Site']]


tonight_df = tonight_df.loc[(tonight_df['Date']==today_np) & (tonight_df['Site']=='home')].reset_index(drop=True)
#Seperating the two EDA dataframes
eda_OU = eda_df.loc[(eda_df['Site']=='home') & (eda_df['Date']<today_np)]
eda_OU.insert(3, "Combined_Rest", eda_OU.loc[:,'Days_Rest'] + eda_OU.loc[:,'Opp_Days_Rest']) 
cut_labels = [500, 1000, 1500, 2000, 3000, 4000]
cut_bins = [0, 500, 1000, 1500, 2000, 3000, 4000]
eda_OU['Distance'] = pd.cut(eda_OU.loc[:,'Opp_distance'], bins=cut_bins, labels= cut_labels)
eda_OU = eda_OU.sort_values('Date').reset_index(drop=True)





# Notify user that the data was successfully loaded.
data_load_state.text('Checking and Fetching Data...Done & done!')

st.write("Check out this [link to the sister site for Team Analysis](https://share.streamlit.io/jfm-data/nhlwagers/main/streamlit_Team.py)")


#############################################
###  Streamlit Design  ######################
############################################


st.subheader("Tonight's Games")
#st.dataframe(tonight_df.style.background_gradient(cmap='viridis', low=0.7, high=0).set_precision(1))
df1 = tonight_df.style.background_gradient(cmap='viridis', low=0.7, high=0).set_precision(1)
df2 = tonight_df.iloc[:,:3].style.set_precision(1)

st.table(df2)
st.dataframe(df1)
######################
## Space for Machine Learning Model
#################### 

st.subheader('Predictions')
st.write('*Coming soon....* :sunglasses:')

st.header('O/U Analysis')

date_select = st.slider(
     "Select Dates",
     datetime.date(2021,1,13), yesterday,
     value=(datetime.date(2021,1,13), yesterday),
     format="MM/DD/YY")
st.write("Start time:", date_select[0])
st.write("Endtime:", date_select[1])

filtered_df= eda_OU[(eda_OU['Date'] >= np.datetime64(date_select[0]))
                       & (eda_OU['Date'] <= np.datetime64(date_select[1]))]



#st.subheader('Overall')
fig_OU = px.histogram(filtered_df, x="Total", color='OUr',
                    barmode='group', template='plotly_dark', title="Totals",
                    color_discrete_map={
    "O":"darkseagreen", 
    "U":"navy", 
    "P":"gold"})
st.plotly_chart(fig_OU, use_container_width=True)

#st.subheader('By Combined Days Rest')
fig_DaysRest = px.histogram(filtered_df[filtered_df["Combined_Rest"] <10],
                            x="Combined_Rest", color='OUr', title='Test',
                   barmode='group', template='plotly_dark', color_discrete_map={
    "O":"darkseagreen", 
    "U":"navy", 
    "P":"gold"})
st.plotly_chart(fig_DaysRest, use_container_width=True)


#st.subheader('By Distance of Road Team from Home')
fig3 = px.histogram(filtered_df, x="Distance", color='OUr',
                   barmode='group', template='plotly_dark',title='By Distance of Road Team from Home',
                   color_discrete_map={
    "O":"darkseagreen", 
    "U":"navy", 
    "P":"gold"})
st.plotly_chart(fig3, use_container_width=True)


#st.subheader('By Length of Road Trip')
fig4 = px.histogram(filtered_df, x="Opp_road_trip", color='OUr',
                   barmode='group', template='plotly_dark', title='By Length of Road Trip',
                   color_discrete_map={
    "O":"darkseagreen", 
    "U":"navy", 
    "P":"gold"})
st.plotly_chart(fig4, use_container_width=True)

#st.subheader('By Length of Home Stand')
fig5 = px.histogram(filtered_df, x="Home_Stand", color='OUr',title='By Length of Home Stand',
                   barmode='group', template='plotly_dark', color_discrete_map={
    "O":"darkseagreen", 
    "U":"navy", 
    "P":"gold"})
st.plotly_chart(fig5, use_container_width=True)



#st.subheader('Select Parameters for situational outputs')

#Filtering For Days of Rest
#Days_to_filter = st.slider('Days of Rest', 0, max(eda_OU.Days_Rest), 3)
#st.text('Number of Days Rest %s' % Days_to_filter)
#filtered_data = eda_OU[eda_OU['Days_Rest'] == Days_to_filter]

#Filtering For Distance
#Distance_to_filter = st.slider('Distance of Opponent', 0.0, max(data.Distance), (0.0, 500.0))
#st.text('Distance From Home %s' % Distance_to_filter[0])
#filtered_data = filtered_data[(filtered_data['Distance'] >= Distance_to_filter[0]) & (filtered_data['Distance'] <= Distance_to_filter[1])]




#Filtering For Home and Away
st.header('O/U Team Analysis -- TO BE MOVED')
team_select = st.selectbox("Select Team",
                 list(pd.unique(eda_df.Team)))
st.write('You selected', team_select)

filtered_data = eda_df[eda_df['Team'] == team_select]

home_away = st.selectbox("Is the Team Home or Away?",
                 ('home', 'away'))
st.write('You selected', home_away)

filtered_data = filtered_data[filtered_data['Site'] == home_away]

days_rest = st.slider('Days Rest', 0, 5, 2)
filtered_data = filtered_data[filtered_data['Days_Rest'] == days_rest]

st.subheader('O/U by Selected Inputs')
fig_OU_team = px.histogram(filtered_data, x="Total", color='OUr',
                    barmode='group', template='plotly_dark')
st.plotly_chart(fig_OU_team, use_container_width=True)

#Filtering For Distance
#Distance_to_filter = st.slider('Distance From Home', 0.0, max(data.Distance), (0.0, 500.0))
#st.text('Distance From Home %s' % Distance_to_filter[0])
#filtered_data = filtered_data[(filtered_data['Distance'] >= Distance_to_filter[0]) & (filtered_data['Distance'] <= Distance_to_filter[1])]


#st.subheader('Selected # of Days on Home Stand')

#st.subheader('Selected # of Days on Road Trip')


#if genre == 'Comedy':
#    st.write('You selected comedy.')
#else:
#    st.write("You didn't select comedy.")



#fig = px.histogram(data, x="Date_diff", color='OUr',
#                   barmode='group', template='plotly_white')
#st.plotly_chart(fig, use_container_width=True)


#st.subheader('Home Stand O/U Results')
#fig1 = px.histogram(data[data["Home_Stand"]>0], x="Home_Stand", color='OUr',
#                    barmode='group', template='plotly_white')
#st.plotly_chart(fig1, use_container_width=True)

#st.subheader('Road Trip O/U Results')
#fig2 = px.histogram(data[data["Road_Trip"]>0], x="Road_Trip", color='OUr',
#                    barmode='group', template='plotly_white')
#st.plotly_chart(fig2, use_container_width=True)

st.header('Unit Analysis')
unit_team = st.selectbox("Select Team for Unit",
                 list(pd.unique(eda_df.Team)))
st.write('You selected', unit_team)


#Filter for OU Line
#Line_to_filter = st.slider('Unit Line', 0.0, max(eda_OU.Total), (0.0, 5.5))
#filtered_data2 = filtered_data[(eda_OU['Total'] >= Line_to_filter[0]) &
#                              (eda_OU['Total'] <= Line_to_filter[1])]



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
    page_title="Hockey Analytics",
    page_icon=":ice_hockey_stick_and_puck:"
)

col1, col2, col3  = st.sidebar.beta_columns([1,7,1])

st.markdown("""<Head>
            <Title> Test Title</Title><link rel="shortcut icon" href="favicon.ico" type="image/x-icon"> </Head>""",unsafe_allow_html=True)

#Title/Header
st.markdown("""<h1 style="text-align:center;color:white;font-weight:bolder;font-size:80px;font-family:helvetica; background:
            -webkit-linear-gradient(#a73305,#000000,#093ff0); -webkit-background-clip:
            text;-webkit-text-fill-color: transparent;">NHL<br>Wager<br>Analytics</h1>""",unsafe_allow_html=True)
# st.markdown('<h1 style="text-align:center;color:white;background-image:url("m1.png");">An analysis..</h1>',unsafe_allow_html=True)
#st.markdown('<h2 style="text-align:center;color:black;">An analysis..</h2>',unsafe_allow_html=True)
#image = Image.open('Betslip.jpg')

#st.title('NHL Wager Analytics - 2021')
#st.image(image, use_column_width=True)


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

eda_df['Units'] = eda_df.apply(lambda x: unit_value(x.Line, x.SUr), axis=1)
eda_df['Total_Units'] = eda_df.groupby('Team')['Units'].cumsum()

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

NHLimage_dict = pd.Series(nhltable.code.values,index=nhltable.Team).to_dict()

# Notify user that the data was successfully loaded.
data_load_state.text('Checking and Fetching Data...Finished Loading!')

#############################################
###  Streamlit Design  ######################
############################################

############ Sidebar Design

st.sidebar.markdown("""<h2 style="text-align:center;color:white;font-weight:bolder;font-size:50px;background:
                    transparent;-webkit-background-clip: text;-webkit-text-fill-color: black;">Team<br>Analytics</h1>""",unsafe_allow_html=True)

st.sidebar.write('*Select Parameters*')

team = st.sidebar.selectbox("Select Team for Analysis",
                 list(pd.unique(eda_df.Team)))
#st.sidebar.write('Team:', team)


image = Image.open(f'NHLimages/{NHLimage_dict[team]}.png')

with col1:
    st.write("")

with col2:
    st.image(image)

with col3:
    st.write("")
    
filtered_data = eda_df[eda_df['Team'] == team]


home_away = st.sidebar.selectbox("Is the Team Home or Away?",
                 ('both', 'home', 'away'))
#st.write('You selected', home_away)
if home_away != "both":
    filtered_data = filtered_data[filtered_data['Site'] == home_away]

dates_team = st.sidebar.slider(
     "Select Dates:",
     datetime.date(2021,1,13), yesterday,
     value=(datetime.date(2021,1,13), yesterday),
     format="MM/DD/YY")
st.sidebar.write("Start :calendar::", dates_team[0].strftime("%b %d %Y"))
st.sidebar.write("End   :calendar::", dates_team[1].strftime("%b %d %Y"))

filtered_data = filtered_data[(filtered_data['Date'] >= np.datetime64(dates_team[0]))
                       & (filtered_data['Date'] <= np.datetime64(dates_team[1]))]

rest_team = st.sidebar.slider(
     "Select Days Between Games(1=B2B):",
     1, 10, value=(1, 10))

#filtered_data = filtered_data[filtered_data['Days_Rest'] == rest_team]

######### Headers
st.subheader("Tonight's Games :ice_hockey_stick_and_puck:")

df1 = tonight_df.iloc[:,:3].rename(columns={'Opp' : 'Away', 'Team':'Home'}).style.set_precision(1)

st.table(df1)
#st.dataframe(tonight_df.style.background_gradient(cmap='viridis', low=0.7, high=0).set_precision(1))


#Filtering For Distance
#Distance_to_filter = st.slider('Distance of Opponent', 0.0, max(data.Distance), (0.0, 500.0))
#st.text('Distance From Home %s' % Distance_to_filter[0])
#filtered_data = filtered_data[(filtered_data['Distance'] >= Distance_to_filter[0]) & (filtered_data['Distance'] <= Distance_to_filter[1])]




#Filtering For Home and Away
st.header('O/U Team Analysis')

OUtable = filtered_data.OUr.value_counts()



fig_OU_team = px.histogram(filtered_data, x="OUr", barmode="group", color="OUr",
                           facet_row="Total", template='plotly_dark')
st.plotly_chart(fig_OU_team, use_container_width=True)

#Filtering For Distance
#Distance_to_filter = st.slider('Distance From Home', 0.0, max(data.Distance), (0.0, 500.0))
#st.text('Distance From Home %s' % Distance_to_filter[0])
#filtered_data = filtered_data[(filtered_data['Distance'] >= Distance_to_filter[0]) & (filtered_data['Distance'] <= Distance_to_filter[1])]

st.header('Unit Team Analysis')

fig_Units_team = px.area(filtered_data, x="Date", y="Total_Units")
#                           facet_row="Total", template='plotly_dark')
st.plotly_chart(fig_Units_team, use_container_width=True)


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


#Filter for OU Line
#Line_to_filter = st.slider('Unit Line', 0.0, max(eda_OU.Total), (0.0, 5.5))
#filtered_data2 = filtered_data[(eda_OU['Total'] >= Line_to_filter[0]) &
#                              (eda_OU['Total'] <= Line_to_filter[1])]



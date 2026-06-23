# Author: Mihir Kawatra
# coding: utf-8

# In[1]:


from pathlib import Path
from dotenv import load_dotenv
import numpy as np
import pandas as pd
import datetime as dt
import re
import pymongo
import os
import sqlalchemy
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from google.cloud import bigquery


# In[7]:


env_path = Path('/home/aurora') / '.env'
load_dotenv(dotenv_path=env_path)


# In[49]:


date = str(dt.datetime.now().date() - dt.timedelta(1))
date_range_list = [str(dt.datetime.now().date() - dt.timedelta(i)) for i in range(1,6)]


# In[9]:


client = bigquery.Client.from_service_account_json('/home/analytics/.secure_files/hitwicketsuperstars-f3e8c620a88c.json')
query = (f"""SELECT count(distinct(user_id)) FROM `hitwicketsuperstars.analytics_190927423.events_{date.replace('-','')}` where event_name='session_start'""")
dau = client.query(query).to_dataframe().iloc[0,0]


# In[10]:


end = dt.datetime.today()
end = end.replace(hour=18, minute=30, second=0, microsecond=0)
start = end - dt.timedelta(5)


# In[11]:


database_username = os.environ['localuser']
database_password = os.environ['pass']
database_ip       = 'localhost'
database_name     = os.environ['dbname']
database_connection = sqlalchemy.create_engine(('mysql+pymysql://{0}:{1}@{2}/{3}'.format(database_username, database_password,database_ip, database_name)))
local_db = database_connection.connect()


# In[95]:


android_retention = pd.read_sql('select * from android_retention_lr',local_db)
android_retention = android_retention.sort_values('date', ascending = False)
android_retention['create_team%'] = (100*android_retention['users']/android_retention['opened_app']).round(1)
android_retention['d1%'] = (100*android_retention['d1']/android_retention['opened_app']).round(1)
android_retention5 = android_retention[["date","opened_app","users","create_team%","d1","d1%"]]
android_retention5['date'] = android_retention5['date'].astype(str)
opened_app = android_retention5[android_retention5['date'] == str(date)]
opened_app = opened_app.iloc[0]['opened_app']
android_retention5 = android_retention5[android_retention5['date'].isin(date_range_list)]
android_retention5.columns = ["date","Opened Hitwicket","Created Team","Created Team %","D1 Retained","D1%"]
android_retention5.set_index('date',inplace=True)


# In[97]:


ios_retention = pd.read_sql('select * from ios_retention_lr',local_db)
ios_retention = ios_retention.sort_values('date', ascending = False)
ios_retention['create_team%'] = (100*ios_retention['users']/ios_retention['opened_app']).round(1)
ios_retention['d1%'] = (100*ios_retention['d1']/ios_retention['opened_app']).round(1)
ios_retention5 = ios_retention[["date","opened_app","users","create_team%","d1","d1%"]]
ios_retention5['date'] = ios_retention5['date'].astype(str)
opened_app = ios_retention5[ios_retention5['date'] == str(date)]
opened_app = opened_app.iloc[0]['opened_app']
ios_retention5 = ios_retention5[ios_retention5['date'].isin(date_range_list)]
ios_retention5.columns = ["date","Opened Hitwicket","Created Team","Created Team %","D1 Retained","D1%"]
ios_retention5.set_index('date',inplace=True)


# In[122]:


html_str = """<html>
<head>
<style>

    h2 {
        font-family: Helvetica, Arial, sans-serif;
    }
    table {
    }
    table, th, td {
        border: 1px solid black;
        border-collapse: collapse;
    }
    th, td {
        padding: 5px;
        font-family: Helvetica, Arial, sans-serif;
        font-size: 100%;
    }
    tbody tr:nth-child(odd) {background: #eee}
    tbody tr:nth-child(even) {background: #fff}
    table tbody tr:hover {
        background-color: #dddddd;
    }
    .wide {

    }

</style>
</head>
<body>
"""


# In[123]:


html_str += f"""
<img src="https://d8tuj5f40nouo.cloudfront.net/images/web/landing/logo.png" width="200" height="83">
<h2>Superstars: {str((dt.datetime.now().date() - dt.timedelta(1)).strftime('%A, %B %d %Y'))}</h2>
<h3>Daily Active Users: {dau}</h3>
"""


# In[124]:


for i in range(len(date_range_list)):
    curr_date = date_range_list[i]
    df = pd.DataFrame(columns = [dt.datetime.strptime(curr_date,'%Y-%m-%d').strftime('%a %d %b %Y')]+list(android_retention5.columns))
    df.set_index(dt.datetime.strptime(curr_date,'%Y-%m-%d').strftime('%a %d %b %Y'),inplace=True)
    df.loc['Android'] = android_retention5.loc[curr_date]
    df.loc['IOS'] = ios_retention5.loc[curr_date]
    total_opened = sum(df['Opened Hitwicket'].tolist())
    total_created = sum(df['Created Team'].tolist())
    total_created_perc = round((100*total_created/total_opened),1)
    total_d1 = sum(df['D1 Retained'].tolist())
    total_d1_perc = round((100*total_d1/total_opened),1)
    df.loc['Total'] = [total_opened,total_created,total_created_perc,total_d1,total_d1_perc]
    df['Opened Hitwicket'] = df['Opened Hitwicket'].apply(lambda x: int(x))
    df['Created Team'] = df['Created Team'].apply(lambda x: int(x))
    df['D1 Retained'] = df['D1 Retained'].apply(lambda x: int(x))
    if(i==0):
        df = df[["Opened Hitwicket", "Created Team", "Created Team %"]]
        signups = str(int(df.loc['Total']['Created Team']))+'('+str(int(df.loc['Total']['Opened Hitwicket']))+')'
    html_str+=f"""
        { df.to_html(index = True) }
        <br><br>
    """
html_str+="<a href=\"https://console.firebase.google.com/u/0/project/hitwicketsuperstars/overview\">Firebase Console</a></body></html>"


# In[125]:


subject = f"""Signups: {signups} - {str((dt.datetime.now().date() - dt.timedelta(1)).strftime('%B %d %Y'))}"""
gmail_user = os.environ['mail']
gmail_password = os.environ['mail_token']
to = ['analytics@hitwicket.com','product@hitwicket.com','growth@hitwicket.com', 'mihir@hitwicket.com']
# to = ['mihir@hitwicket.com','anshaj@hitwicket.com']
sent_from = gmail_user
text = "Please use an html reader"
message = MIMEMultipart("alternative", None, [MIMEText(text), MIMEText(html_str,'html')])
message['From'] = "Analytics <" + os.environ['mail'] + ">"
message['Subject'] = subject


# In[126]:

s = smtplib.SMTP('smtp.gmail.com', 587)
s.starttls()
s.login(gmail_user, gmail_password)
s.sendmail(sent_from, to, message.as_string())
s.quit()

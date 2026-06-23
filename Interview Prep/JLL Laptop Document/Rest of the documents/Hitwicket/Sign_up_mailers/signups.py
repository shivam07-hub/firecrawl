#!/home/aurora/miniconda3/bin/python
# Author: Mihir Kawatra
try:
    # In[10]:
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
    

    # In[11]:


    env_path = Path('/home/aurora') / '.env'
    load_dotenv(dotenv_path=env_path)

    # In[12]:


    date = str(dt.datetime.now().date() - dt.timedelta(1))
    print(date+'\n---------------------------------------------------------------------------\n')
    date_range_list = [str(dt.datetime.now().date() - dt.timedelta(i)) for i in range(1,6)]


    # In[13]:


    client = bigquery.Client.from_service_account_json('/home/analytics/.secure_files/hitwicketsuperstars-f3e8c620a88c.json')
    query = (f"""SELECT count(distinct(user_id)) FROM `hitwicketsuperstars.analytics_190927423.events_{date.replace('-','')}` where event_name='session_start'""")
    dau = client.query(query).to_dataframe().iloc[0,0]

    print("Fetched DAU from BigQuery")
    # In[14]:


    end = dt.datetime.today()
    end = end.replace(hour=18, minute=30, second=0, microsecond=0)
    start = end - dt.timedelta(5)


    # In[15]:

    print("Fetching Data from MYSQL")
    database_username = os.environ['localuser']
    database_password = os.environ['pass']
    database_ip       = 'localhost'
    database_name     = os.environ['dbname']
    database_connection = sqlalchemy.create_engine(('mysql+pymysql://{0}:{1}@{2}/{3}'.format(database_username, database_password,database_ip, database_name)))
    local_db = database_connection.connect()


    # In[21]:


    android_retention = pd.read_sql('select * from android_retention_lr',local_db)
    android_retention = android_retention.sort_values('date', ascending = False)
    android_retention['create_team%'] = (100*android_retention['users']/android_retention['opened_app']).round(1)
    android_retention['d1%'] = (100*android_retention['d1']/android_retention['opened_app']).round(1)
    android_retention5 = android_retention[["date","opened_app","users","create_team%","d1","d1%"]]
    android_retention5['date'] = android_retention5['date'].astype(str)
    opened_app = android_retention5[android_retention5['date'] == str(date)]
    opened_app = opened_app.iloc[0]['opened_app']
    android_retention5 = android_retention5[android_retention5['date'].isin(date_range_list)]
    android_retention5.columns = ["date","New Installs","Team Creation","Team Creation %","D1 Retained","D1%"]
    android_retention5.set_index('date',inplace=True)


    # In[22]:


    ios_retention = pd.read_sql('select * from ios_retention_lr',local_db)
    ios_retention = ios_retention.sort_values('date', ascending = False)
    ios_retention['create_team%'] = (100*ios_retention['users']/ios_retention['opened_app']).round(1)
    ios_retention['d1%'] = (100*ios_retention['d1']/ios_retention['opened_app']).round(1)
    ios_retention5 = ios_retention[["date","opened_app","users","create_team%","d1","d1%"]]
    ios_retention5['date'] = ios_retention5['date'].astype(str)
    opened_app = ios_retention5[ios_retention5['date'] == str(date)]
    opened_app = opened_app.iloc[0]['opened_app']
    ios_retention5 = ios_retention5[ios_retention5['date'].isin(date_range_list)]
    ios_retention5.columns = ["date","New Installs","Team Creation","Team Creation %","D1 Retained","D1%"]
    ios_retention5.set_index('date',inplace=True)


    # In[161]:


    def d1_color_setter(value):
        if value <= 4:
            color = 'red'
        elif value >= 8:
            color = 'green'
        else:
            color = 'none'
        return 'color: %s' % color


    # In[162]:


    def ct_color_setter(value):
        if value <= 20:
            color = 'red'
        elif value >= 30:
            color = 'green'
        else:
            color = 'none'
        return 'color: %s' % color


    # In[138]:


    def bold(value):
        return 'font-weight: bold;'


    # In[278]:

    print("Preparing Mail")
    html_str = """<html>
    <head>
    <style>

        h2 {
            font-family: Helvetica, Arial, sans-serif;
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
        table tbody tr td:hover {
            background-color: #fcffb2;
        }
        .col_heading{
            font-weight: normal;
        }
        .row0, .row1{
            font-weight: normal;
        }
        .row_heading, .blank{
            display: none;
        }
        .row0, .row2{
            background-color: #dddddd;
        }
        .row0:hover, .row2:hover{
            background-color: #fcffb2;
        }
        .row2{
            font-weight: bold;
        }
        .col1, .col2, .col3, .col4, .col5{
            text-align: right;
        }
    </style>
    </head>
    <body>
    """


    # In[279]:


    html_str+=f""" 
    <img src="https://d8tuj5f40nouo.cloudfront.net/images/web/landing/logo.png" width="200" height="83">
    <h2>Superstars: {str((dt.datetime.now().date() - dt.timedelta(1)).strftime('%A, %B %d'))}</h2>
    <h3>Daily Active Users: {dau}</h3>
    """


    # In[280]:


    for i in range(len(date_range_list)):
        curr_date = date_range_list[i]
        l=[]
        l.append(['Android'] + list(android_retention5.loc[curr_date]))
        l.append(['IOS'] + list(ios_retention5.loc[curr_date]))
        df = pd.DataFrame(l, columns = [dt.datetime.strptime(curr_date,'%Y-%m-%d').strftime('%A, %d %b')]+list(android_retention5.columns))
        total_opened = sum(df['New Installs'].tolist())
        total_created = sum(df["Team Creation"].tolist())
        total_created_perc = round((100*total_created/total_opened),1)
        total_d1 = sum(df['D1 Retained'].tolist())
        total_d1_perc = round((100*total_d1/total_opened),1)
        df.loc[len(df)] = (['Total'] + [total_opened,total_created,total_created_perc,total_d1,total_d1_perc])
        df['New Installs'] = df['New Installs'].apply(lambda x: int(x))
        df["Team Creation"] = df["Team Creation"].apply(lambda x: int(x))
        df['D1 Retained'] = df['D1 Retained'].apply(lambda x: int(x))
        if(i==0):
            df = df[[df.columns[0],"New Installs", "Team Creation", "Team Creation %"]]
            signups = str(int(df.iloc[len(df)-1]['New Installs'])) + '(' + str(int(df.iloc[len(df)-1]["Team Creation"])) + ')'
            df = df.style.applymap(ct_color_setter,subset=['Team Creation %'])
        else:
            df = df.style.applymap(d1_color_setter,subset=['D1%']).applymap(ct_color_setter,subset=['Team Creation %'])
        df_str = df.render(index = False).replace('\n','')
        html_str+= f"""
            { df_str }
            <br><br>
        """
    html_str+="<a href=\"https://console.firebase.google.com/u/0/project/hitwicketsuperstars/overview\">Firebase Console</a></body></html>"


    # In[ ]:


    html_str = html_str.replace('\n','')


    # In[281]:

    print("Sending Mail")
    subject = f"""Superstars Users: {signups} - {str((dt.datetime.now().date() - dt.timedelta(1)).strftime('%B %d'))}"""
    gmail_user = os.environ['mail']
    gmail_password = os.environ['mail_token']
    to = ['digest_users@hitwicket.com']
    # to=['mihir@hitwicket.com']
    sent_from = gmail_user
    text = "Please use an html reader"
    message = MIMEMultipart("alternative", None, [MIMEText(text), MIMEText(html_str,'html')])
    message['To'] = 'digest_users@hitwicket.com'
    message['From'] = "Analytics <" + os.environ['mail'] + ">"
    # message['Bcc'] = 'mihir@hitwicket.com'
    message['Subject'] = subject


    # In[282]:


    s = smtplib.SMTP('smtp.gmail.com', 587)
    s.starttls()
    s.login(gmail_user, gmail_password)
    s.sendmail(sent_from, to, message.as_string())
    s.quit()
    print("Mail sent")
    # Author: Mihir Kawatra

except:
    from slacker import Slacker
    slack = Slacker(os.environ['accio'])
    if slack.api.test().successful:
        print( f"Connected to {slack.team.info().body['team']['name']}.")
    else:
            print('Try Again!')
    slack.chat.post_message(channel='cron',
                            text="Cron-job for Signups Mailer on " + str(dt.date.today()) + " has failed.", 
                            username='accio')     

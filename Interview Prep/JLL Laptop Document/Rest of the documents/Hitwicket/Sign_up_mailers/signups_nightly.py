#!/home/aurora/miniconda3/bin/python
# Author: Mihir Kawatra
try:
    # In[10]:
    from bson import ObjectId
    from flatten_json import flatten
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
    from bs4 import BeautifulSoup
    import json
    import requests

    # In[2]:


    env_path = Path('/home/aurora') / '.env'
    load_dotenv(dotenv_path=env_path)


    # In[149]:


    date = str(dt.datetime.now().date() - dt.timedelta(1))
    print(str(dt.date.today())+'\n---------------------------------------------------------------------------\n')
    date_range_list = [str(dt.datetime.now().date() - dt.timedelta(i)) for i in range(1,5)]


    # In[4]:
    print("Fetching DAU from BigQuery")

    client = bigquery.Client.from_service_account_json('/home/analytics/.secure_files/hitwicketsuperstars-f3e8c620a88c.json')
    query = (f"""SELECT count(distinct(user_id)) FROM `hitwicketsuperstars.analytics_190927423.events_intraday_{str(dt.date.today()).replace('-','')}` where event_name='screen_view'""")
    dau = client.query(query).to_dataframe().iloc[0,0]

    

    # In[7]:
    print("Fetching New Devices from BigQuery")

    bq_table_str = (f"hitwicketsuperstars.analytics_190927423.events_intraday_{str(dt.date.today()).replace('-','')}")
    query = (
        f"""SELECT
      user_id,
      MIN(event_timestamp),
      platform
    FROM
      `{bq_table_str}`
    WHERE app_info.id = 'cricketgames.hitwicket.strategy'
    GROUP BY
      user_id,
      platform"""
    )
    new_devices_today = client.query(query).to_dataframe()
    query = (
        f"""SELECT
        * FROM
        `hitwicketsuperstars.analytics_190927423.new_user_reference`"""
    )
    new_user_reference = client.query(query).to_dataframe()

    new_devices_today = new_devices_today[~new_devices_today["user_id"].isin(new_user_reference["device_id"])]
    new_devices_today.columns = ['device_id', 'user_first_touch_timestamp','platform']
    new_devices_today['user_first_touch_timestamp'] = pd.to_datetime(new_devices_today['user_first_touch_timestamp'], unit = 'us')
    new_devices_today['user_first_touch_timestamp'] = new_devices_today['user_first_touch_timestamp'].astype('datetime64[s]')


    # In[11]:
    print("Fetching Today's data from Mongo")

    cursor = pymongo.MongoClient("mongodb://" + os.environ['user'] + ':' +
                                 os.environ['pass'] + '@' + os.environ['db1']  + "/?authSource=" +
                                 os.environ['dbname'])
    db = cursor.superstars
    aw = list(db.users.find({}, {'login_details.last_request_at', 'sign_up_details.device.id', 'created_at'}))
    all_users = pd.DataFrame([flatten(d) for d in aw])
    all_users = all_users.sort_values(['sign_up_details_device_id','created_at'])
    all_users = all_users.drop_duplicates('sign_up_details_device_id')
    the_merge = pd.merge(new_devices_today, all_users, left_on='device_id', right_on='sign_up_details_device_id', how = 'left')
    the_merge['time_diff'] = the_merge['login_details_last_request_at'] - the_merge['user_first_touch_timestamp']
    the_merge['d1'] = (the_merge['time_diff'] >= pd.Timedelta('1 days 00:00:00')).astype(int)
    the_merge['date'] = the_merge['user_first_touch_timestamp'].dt.date


    # In[62]:


    android = the_merge[the_merge.platform == 'ANDROID']
    ios = the_merge[the_merge.platform == 'IOS']


    # In[63]:


    and_grouped = android.groupby('date').agg({'device_id' : 'count', '_id' : 'count'})
    ios_grouped = ios.groupby('date').agg({'device_id' : 'count', '_id' : 'count'})


    # In[12]:


    end = dt.datetime.today()
    end = end.replace(hour=18, minute=30, second=0, microsecond=0)
    start = end - dt.timedelta(5)


    # In[13]:
    print("Fetching data for the past 4 days from MySQL")

    database_username = os.environ['localuser']
    database_password = os.environ['pass']
    database_ip       = 'localhost'
    database_name     = os.environ['dbname']
    database_connection = sqlalchemy.create_engine(('mysql+pymysql://{0}:{1}@{2}/{3}'.format(database_username, database_password,database_ip, database_name)))
    local_db = database_connection.connect()


    # In[34]:


    android_retention = pd.read_sql('select * from android_retention_lr',local_db)
    android_retention = android_retention.sort_values('date', ascending = False)
    android_retention['create_team%'] = (100*android_retention['users']/android_retention['opened_app']).round(1)
    android_retention['d1%'] = (100*android_retention['d1']/android_retention['opened_app']).round(1)
    android_retention5 = android_retention[["date","opened_app","users","create_team%","d1","d1%"]]
    android_retention5['date'] = android_retention5['date'].astype(str)
    # print(android_retention5)
    opened_app = android_retention5[android_retention5['date'] == str(date)]
    # print(opened_app)
    opened_app = opened_app.iloc[0]['opened_app']
    android_retention5 = android_retention5[android_retention5['date'].isin(date_range_list)]
    android_retention5.columns = ["date","New Installs","Created Team","Created Team %","D1 Retained","D1%"]
    android_retention5.set_index('date',inplace=True)


    # In[91]:


    latest = and_grouped.iloc[-1]
    latest['team_create_perc'] = ((latest['_id']/latest['device_id'])*100).round(1)
    latest = latest.tolist()
    latest+=[0,0]
    android_retention5.loc[str(dt.date.today())] = latest
    android_retention5 = android_retention5.sort_index(ascending=False)


    # In[72]:


    ios_retention = pd.read_sql('select * from ios_retention_lr',local_db)
    ios_retention = ios_retention.sort_values('date', ascending = False)
    ios_retention['create_team%'] = (100*ios_retention['users']/ios_retention['opened_app']).round(1)
    ios_retention['d1%'] = (100*ios_retention['d1']/ios_retention['opened_app']).round(1)
    ios_retention5 = ios_retention[["date","opened_app","users","create_team%","d1","d1%"]]
    ios_retention5['date'] = ios_retention5['date'].astype(str)
    opened_app = ios_retention5[ios_retention5['date'] == str(date)]
    # print(opened_app)
    opened_app = opened_app.iloc[0]['opened_app']
    ios_retention5 = ios_retention5[ios_retention5['date'].isin(date_range_list)]
    ios_retention5.columns = ["date","New Installs","Created Team","Created Team %","D1 Retained","D1%"]
    ios_retention5.set_index('date',inplace=True)


    # In[98]:


    latest = ios_grouped.iloc[-1]
    latest['team_create_perc'] = ((latest['_id']/latest['device_id'])*100).round(1)
    latest = latest.tolist()
    latest+=[0,0]
    ios_retention5.loc[str(dt.date.today())] = latest
    ios_retention5 = ios_retention5.sort_index(ascending=False)


    # In[100]:


    def d1_color_setter(value):
        if value <= 4:
            color = 'red'
        elif value >= 8:
            color = 'green'
        else:
            color = 'none'
        return 'color: %s' % color


    # In[101]:


    def ct_color_setter(value):
        if value <= 20:
            color = 'red'
        elif value >= 30:
            color = 'green'
        else:
            color = 'none'
        return 'color: %s' % color


    # In[102]:


    def bold(value):
        return 'font-weight: bold;'


    # In[150]:
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

    # In[150]:
    
    print("Scraping Data from PlayStore")
    r = requests.get('https://play.google.com/store/apps/details?id=cricketgames.hitwicket.strategy&hl=en_IN')
    htmlResult = BeautifulSoup(r.content, "html.parser")
    rating = htmlResult.find(class_='BHMmbe').get_text()
    num_people = htmlResult.find(class_='EymY4b').find_all()[1].get_text()
    filename = '/home/aurora/bucket/play_store_reviews/reviews_'+str(dt.date.today()).replace('-','')+'.json'
    try:
        df = pd.read_json(filename).sort_values(['rank']).reset_index(drop=True)
        num_today = len(df)
    except:
        num_today = 0
    # In[151]:


    html_str+=f"""
    <img src="https://d8tuj5f40nouo.cloudfront.net/images/web/landing/logo.png" width="200" height="83">
    <h2>Superstars: {str((dt.datetime.now().date()).strftime('%A, %B %d'))}</h2>
    <h3>Daily Active Users: {dau}</h3>
    <h3>Current Play Store Rating: {rating}({num_today} Reviews Yesterday)</h3>
    """


    # In[152]:


    date_range_list+=[str(dt.date.today())]
    date_range_list=sorted(date_range_list)[::-1]
    for i in range(len(date_range_list)):
        curr_date = date_range_list[i]
        l=[]
        l.append(['Android'] + list(android_retention5.loc[curr_date]))
        l.append(['IOS'] + list(ios_retention5.loc[curr_date]))
        df = pd.DataFrame(l, columns = [dt.datetime.strptime(curr_date,'%Y-%m-%d').strftime('%A, %d %b')]+list(android_retention5.columns))
        total_opened = sum(df['New Installs'].tolist())
        total_created = sum(df['Created Team'].tolist())
        total_created_perc = round((100*total_created/total_opened),1)
        total_d1 = sum(df['D1 Retained'].tolist())
        total_d1_perc = round((100*total_d1/total_opened),1)
        df.loc[len(df)] = (['Total'] + [total_opened,total_created,total_created_perc,total_d1,total_d1_perc])
        df['New Installs'] = df['New Installs'].apply(lambda x: int(x))
        df['Created Team'] = df['Created Team'].apply(lambda x: int(x))
        df['D1 Retained'] = df['D1 Retained'].apply(lambda x: int(x))
        if(i==0):
            df = df[[df.columns[0],"New Installs", "Created Team", "Created Team %"]]
            signups = str(int(df.iloc[len(df)-1]['New Installs'])) + '(' + str(int(df.iloc[len(df)-1]['Created Team'])) + ')'
            df = df.style.applymap(ct_color_setter,subset=['Created Team %'])
        else:
            df = df.style.applymap(d1_color_setter,subset=['D1%']).applymap(ct_color_setter,subset=['Created Team %'])
        df_str = df.render(index = False).replace('\n','')
        html_str+= f"""
            { df_str }
            <br><br>
        """
    html_str+="<a href=\"https://console.firebase.google.com/u/0/project/hitwicketsuperstars/overview\">Firebase Console</a></body></html>"
    print("Getting Latest Playstore Reviews from Bucket")
    html_str+="<h2>Play Store Reviews: "
    try:
        filename = '/home/aurora/bucket/play_store_reviews/reviews_'+str(dt.date.today()).replace('-','')+'.json'
        df = pd.read_json(filename).sort_values(['rank']).reset_index(drop=True)
        if len(df) > 0:
            html_str+="</h2><ul>"
            for i in range(len(df)):
                html_str+=f"<li>{df.iloc[i]['author']}: ({df.iloc[i]['rank']} \u2B50) {df.iloc[i]['reviewText']}</li>"
            html_str+="</ul>"
        else:
            html_str+="None</h2>"
    except:
        print("File Not Found")
        html_str+="None</h2>"
    
    # In[153]:


    html_str = html_str.replace('\n','')


    # In[154]:
    print("Sending Mail")

    subject = f"""Superstars Users: {signups} - {str((dt.datetime.now().date()).strftime('%B %d'))}"""
    gmail_user = os.environ['mail']
    gmail_password = os.environ['mail_token']
    to = ['digest_users@hitwicket.com']
    # to = ['mihir@hitwicket.com']
    sent_from = gmail_user
    text = "Please use an html reader"
    message = MIMEMultipart("alternative", None, [MIMEText(text), MIMEText(html_str,'html')])
    message['To'] = ','.join(to)
    message['From'] = "Analytics <" + os.environ['mail'] + ">"
    message['Subject'] = subject


    # In[155]:


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
    # print(a)

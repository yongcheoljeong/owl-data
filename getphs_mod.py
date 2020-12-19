## Import packages
import pandas as pd
import csv
from tqdm import tqdm
import time
import json
import pymysql
from sqlalchemy import create_engine
import sys
import collections

## Connect to MySQL DB
# Credentials to DB connection
hostname = "localhost" 
username = "root"
pwd = "gpdlzjadh"
dbname = "esd_phs"
charset = "utf8"

# Create connection to MySQL DB
conn = pymysql.connect(host=hostname, user=username, password=pwd, db=dbname, charset=charset)
cur = conn.cursor()

# Get table names from mysql db
db_name = 'esd_phs'

## Set Dir and Headers
# file dir setting
filename = 'payload_playerherostats-20200831-20200906.tsv/payload_playerherostats-20200831-20200906.tsv'

# headers = ['time', 'hero_guid', 'stat_lifespan', 'stat', 'player', 'team', 'esports_match_id']
headers_asis = ['time', 'hero_guid', 'stat_lifespan']
json_type_headers = ['stat', 'player', 'team']
stat_json_interest_headers = ['short_stat_guid', 'amount']
player_json_interest_headers = ['battletag', 'esports_player_id']
team_json_interest_headers = ['esports_team_id']

## Get guids
# hero_guid
hero_guid_dict = dict()
with open('guid/hero_guid.csv', newline='', encoding = 'utf-8') as csv_hero_guid:
    csv_reader = csv.DictReader(csv_hero_guid)
    for row in csv_reader:
        hero_guid_dict[row['en_hero_name']] = row['guid']

# # map_guid
# map_list = []
# with open('guid/map_guid.csv', newline='', encoding = 'utf-8') as csv_map_guid:
#     csv_reader = csv.DictReader(csv_map_guid)
#     for row in csv_reader:
#         map_list.append(row[x] for x in ['guid', 'en_map_name'])

# # stat_guid
# stat_list = []
# with open('guid/stat_guid.csv', newline='', encoding = 'utf-8') as csv_stat_guid:
#     csv_reader = csv.DictReader(csv_stat_guid)
#     for row in csv_reader:
#         stat_list.append(row[x] for x in ['statcategory', 'ssg', 'en_stat_name'])

## Calculate the running time
start_time = time.time()

## Define funcs and vars
def get_table_names(name):
    query = f"SELECT table_name FROM information_schema.tables WHERE table_schema = '{name}';"
    
    cur.execute(query) 
    tables = cur.fetchall()
    table_names = list()
    for t in tables:
        table_names.append(t[0])
    
    return table_names

table_names = get_table_names(db_name)

# {'table_name': [], 'table_name2': [] ...}
table_data_list = collections.defaultdict(list)

# add to table_names list

def create_table(name):
    query = f'''CREATE TABLE `{name}` (
    `index` int NOT NULL AUTO_INCREMENT,
    `time` varchar(14) DEFAULT NULL,
    `hero_guid` varchar(20) DEFAULT NULL,
    `stat_lifespan` varchar(20) DEFAULT NULL,
    `hero_name` varchar(20) DEFAULT NULL,
    `short_stat_guid` float DEFAULT NULL,
    `amount` float DEFAULT NULL,
    `battletag` varchar(40) DEFAULT NULL,
    `esports_player_id` float DEFAULT NULL,
    `esports_team_id` float DEFAULT NULL,
    PRIMARY KEY (`index`),
    KEY `time` (`time`)
    )'''
    cur.execute(query)

## Read csv file and insert into the DB
n = 0
with open(filename, newline='') as csv_file:
    csv_reader = csv.DictReader(csv_file, delimiter = '\t')
    mod = sys.modules[__name__]
    for row in tqdm(csv_reader, desc = 'num row'):
        n += 1
        esports_match_id = row['esports_match_id'] # esports_match_id 따로 빼서 비교
        table_name = f'match_{esports_match_id}'
        data = [row[x] for x in headers_asis]

        #get hero_name here
        guid_search = row['hero_guid']
        hero_name = [hero_name for hero_name, hero_guid in hero_guid_dict.items() if hero_guid == guid_search]
        if len(hero_name) == 0:
            hero_name = ['no match']
        data.extend(hero_name)

        stat_json = json.loads(row['stat'])
        data.extend([stat_json[x] for x in stat_json_interest_headers])

        player_json = json.loads(row['player'])
        data.extend([player_json[x] for x in player_json_interest_headers])

        team_json = json.loads(row['team'])
        data.extend([team_json[x] for x in team_json_interest_headers])
        
        # if esports_match_id not exists in table_names
        if (table_name) not in table_names:
            
            # create table in mysql here
            create_table(table_name) # create table as 'match_{esports_match_id}'
            table_names.append(table_name)
        
        table_data_list[table_name].append(tuple(data))

        if n == 1000000: # insert to the DB every 100000 interations
            
            for each_table in table_names:
                sql = f"INSERT INTO esd_phs.{each_table} (time, hero_guid, stat_lifespan, hero_name, short_stat_guid, amount, battletag, esports_player_id, esports_team_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
                cur.executemany(sql, table_data_list[each_table])
                table_data_list[each_table].clear() # reset the dict 
            
            conn.commit()
            n = 0
            continue

# insert rest of the data
if n != 0:
    for each_table in table_names:
        sql = f"INSERT INTO esd_phs.{each_table} (time, hero_guid, stat_lifespan, hero_name, short_stat_guid, amount, battletag, esports_player_id, esports_team_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
        cur.executemany(sql, table_data_list[each_table])
        table_data_list[each_table].clear() # reset the dict 
    n = 0

conn.commit()
cur.close()
conn.close()
end_time = time.time() - start_time
print(end_time)
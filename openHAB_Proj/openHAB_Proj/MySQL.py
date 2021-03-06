#!/usr/bin/env python

#Author    - Warren Kavanagh 
#Last edit - 00/05/2020


##Description##
#This module contains functions for interfacing with the community_grid database
#It allows connection to the database and to store values in the databases tables
#The database currently contains the following tables:
#   1.Hubs          - Information on each of the hubs in the network
#   2.Devices       - Contains information on the smart devices in the network 
#   3.Items         - Contains information on the items associated with devices in the network
#   4.Meter_Values  - Contains the most up to date meter readings 
#   4.All_Values    - Contains a record of meter readings 



##Modules to import##
# mysql.connector  - Module which contains the functionallity to connect to the MySQL Database
# ConfigParser     - Module to parse configuration files, used to get database config
# Logging          - Module used to log to the log file for this file
# sys              - Sets up stream handler for module
# asyncio          - Implments the asynchrounous function calls
# aiomysql         - Implemmtns the asynchrounous databse querys/logs
# datetime         - Used to get the current date time 
from mysql.connector import MySQLConnection, Error
from configparser import ConfigParser
import logging
import sys
import asyncio
import aiomysql
from datetime import datetime

###Set up logger##
##get the logger
logger = logging.getLogger(__name__) #Get the logger
logger.setLevel(logging.INFO) #Set the log level 
#set up the formatting 
formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(process)d:%(processName)s:%(filename)s:%(message)s')#Crete a formatter
#setup the file handler 
file_handler=logging.FileHandler('/home/openhabian/Environments/env_1/openHAB_Proj/lib/logs/MySQL.log')#Get a file handler
file_handler.setFormatter(formatter)
#file_handler.setLevel(logging.ERROR)
file_handler.setLevel(logging.INFO)
#setup a stream handler
stream_handler = logging.StreamHandler(sys.stdout) # get a stream hander 
stream_handler.setLevel(logging.ERROR) #set the stream handler level 
#Add the handlers to the logger
logger.addHandler(file_handler) #Add the handler to logger 
logger.addHandler(stream_handler)


##Function List##
#   read_db_config    - Reads the configuration file for mysql retruns the configuration parameters
#                       in a dictionary
#   connect           - Connects to a mysql database using a config file returned from read_db_config
#   update_items      - Updates an multiple enrtys in the items table at once 
#   insert_items      - Inserts multiple item entrys into the items table, if entrys exists calls 
#                       the update_items
#   hub_data          - This function populates the hubs table in the database with an entry 
#   insert_device     - Inserts a row into the device table of the community_grid database 
#   query_all_values  - Querys the meter_vales table for most up to date power readings
#   update_all_values - Updates the all_values and meter_values tables

##read_db_config##
#Reads the configuration file for mysql
#retruns the configuration parameters for in a dictionary
#Inputs:
#   filename - The name of the configuration file 
#   section  - The section of the config file to read from 
#Return
#   db  - Configuration parameters to access database in a dictionary 
def read_db_config(filename='/home/openhabian/Environments/env_1/openHAB_Proj/openHAB_Proj/config.ini',section='mysql'):
    # create parser and read ini configuration file
    parser = ConfigParser()
    parser.read(filename)
    logger.info(f"Parsing file {filename}")

    # get section, default to mysql
    db = {}
    if parser.has_section(section):
        items = parser.items(section)
        # Fill the db dictionary with the key and value pairs from
        # the configuration file
        for item in items:
            db[item[0]] = item[1]
    else:
        logger.error(f'{section} no found in the {filename} file')
        raise Exception(f'{section} no found in the {filename} file')
    logger.info(f"Database Configuration:{db}")
    return db


##connect##
#This connects to a mysql database using a config file
#Calls the function read_db_config which parsers the config.ini file
#Then establishes connection based on the config parameters with the 
#function MySQLConnection
#Return:
#   conn - A MySQLConnection object
async def connect():
    db_config = read_db_config()
    #print(help(aiomysql.create_pool)
    try:
        logger.info('Attempting to connect to MySQL database')
        conn = await aiomysql.connect(db='community_grid',read_default_file ='/home/openhabian/Environments/env_1/openHAB_Proj/openHAB_Proj/config.ini' )
        logger.info(f"Connection established at IP:{conn._host} Database:{conn._db}")
        return conn
    except Exception as e:
        logger.exception(f"Connection to database failed, tracback shown below\n{e}")



##update_item##
#Updates an enrty in the items table 
#An entry will be updated if the table contains a duplicate primary key of ItemUID
#Inputs:
#   item - A list containing tuples of items to update with the ItemUID last 
async def update_items(item,conn):
    query = ''' UPDATE items
                SET DeviceID =%s,
                Value = %s,
                Units = %s,
                Time  = %s
                WHERE 
                ItemUID = %s
    '''
    #Try to insert to table
    try:
        logger.info("Attempting to update items table")
        async with conn.cursor() as cur:
            # execute the query
            await cur.executemany(query,item)
            # Commit the query 
            await conn.commit()
            logger.info(f"Items table has been updated updated{item}")

    #Print the error out
    except Exception as e:
        logger.exception(f"Could not update the items table, traceback shown below\n{e}")

    #Close the connection
    finally:
        await cur.close()

##insert_item##
#Inserts sseveral entrys into the community_grid database table items
#If the entry already exists it will be updated using the update_item
#The item table has the schema 
#+----------+--------------+------+-----+---------+-------+
#| Field    | Type         | Null | Key | Default | Extra |
#+----------+--------------+------+-----+---------+-------+
#| ItemUID  | varchar(255) | NO   | PRI | NULL    |       |
#| DeviceID | varchar(255) | YES  | MUL | NULL    |       |
#| Value    | int          | YES  |     | NULL    |       |
#| Units    | varchar(255) | YES  |     | NULL    |       |
#| Time     | datetime     | YES  |     | NULL    |       |
#+----------+--------------+------+-----+---------+-------+
#Inputs:
#   items - A list contating multiple tuples which have values for ItemUID,DeviceID,Value,Units,Time in 
#           that order or single tuple
async def insert_item(items,conn):
    query = '''INSERT INTO items(ItemUID,DeviceID,Value,Units,Time)
               VALUES(%s,%s,%s,%s,%s)'''
    #Try to insert to table
    try:
        async with conn.cursor() as cur:
            # execute the query
            await cur.executemany(query,items)
            # Commit the query 
            await conn.commit()
            logger.info(f"Items table has been updated updated{items}")
    #Print the error out
    except Exception as e:
        code, message = e.args
        #The entry is duplicate detected by error code 1062
        if code == 1062:
            logger.warning(f"Duplicate entry in items table {items}")
            item = list()
            ID = list()
            # Recorganize each tuple to pass to the update_items function
            # The ItemUID must be last in each tuple, look at the query in update_items function 
            for val in items:
                a = (val[1:5]+(val[0],))
                item.append(a)
            await update_items(item,conn)
        else:
            logger.error(e)
    #Close the connection
    finally:
        await cur.close()

##hub_data##
#This function populates the hubs table in the database
#The hubs table has the following columns 
#| Field         | Type         | Null | Key | Default | Extra |
#+---------------+--------------+------+-----+---------+-------+
#| RaspberryPi_ID | varchar(255) | NO   | PRI | NULL    |       |
#| IP_Address    | varchar(255) | YES  |     | NULL    |       |
#| Location      | varchar(255) | YES  |     | NULL    |       |
#Inputs
    #MAC - The MAC address of the Raaspberry Pi 
    #IP  - The IP address of the Raspberry Pi 
#The Location will have to be manually set as the location of the IP server can only be found
async def hub_data(MAC,IP,Time,conn):
    try:
        query = '''INSERT INTO hubs(RaspberryPi_ID,IP_Address,Time,Location)
               VALUES(%s,%s,%s,"Dublin")'''

        async with conn.cursor() as cur:
            logger.info("Attempting to update hub table")
            await cur.execute(query,(MAC,IP,Time))
            await conn.commit()
            logger.info(f"Hub data entry {MAC} insereted into hub table")
    except Exception as e:
        code, message = e.args
        if code == 1062:
            logger.warning(f"Entry {MAC} exists, attempting to update table entry")
            #Update the value for this primary key
            query = '''UPDATE hubs
                SET IP_Address = %s,
                Time = %s,
                Location = "Dublin"
                WHERE 
                RaspberryPi_ID = %s'''
            try:
                async with conn.cursor() as cur:
                    await cur.execute(query,(IP,Time,MAC))
                    await conn.commit()
                    logger.info(f"Entry {MAC} has been updated in hubs table")
            except Exception as e:
                logger.exception(f"Updating hub data entry of {MAC} failed\n{e}")
        else: 
            logger.exception(f"Could not insert data entry identified by {MAC} into hubs table\n{e}")
    finally:
        await cur.close()

##insert_device##
#This function inserts an entry into the devices table of the community grid database 
#The devices table has the following columns 
#Field                  | Type         | Null | Key | Default | Extra |
#+------------------------+--------------+------+-----+---------+-------+
#| DeviceID               | varchar(255) | NO   | PRI | NULL    |       |
#| RaspberryPi_ID         | varchar(255) | YES  | MUL | NULL    |       |
#| Status                 | varchar(255) | YES  |     | NULL    |       |
#| Status_Detail          | varchar(255) | YES  |     | NULL    |       |
#| Communication_Protocol | varchar(255) | YES  |     | NULL    |       |
#| Binding                | varchar(255) | YES  |     | NULL    |       |
#+------------------------+--------------+------+-----+---------+-------+
async def insert_device(DeviceID,RaspberryPi_ID,Status,Status_Detail,
                        Status_Desc,Communication_Protocol,Binding,Time,conn):
    query = ''' INSERT INTO devices(DeviceID,RaspberryPi_ID,Status,Status_Detail,Status_Description,
                                    Communication_Protocol,Binding,Time)
               VALUES(%s,%s,%s,%s,%s,%s,%s,%s)
    '''

    #Try to insert to table
    try:
        async with conn.cursor() as cur:
            logger.info(f"Attempting to insert {DeviceID} into devices table")
            await cur.execute(query,(DeviceID,RaspberryPi_ID,Status,Status_Detail,Status_Desc,Communication_Protocol,Binding,Time))
            await conn.commit()
            logger.info(f"{DeviceID} entry added to devices table")
    
    #Print the error out
    except Exception as e:
        code, message = e.args
        if code == 1062:
            logger.warning(f"Entry {DeviceID} exists, attempting to update entry")
            query = '''UPDATE devices
                SET 
                RaspberryPi_ID =%s,
                Status =%s,
                Status_Detail = %s,
                Status_Description = %s,
                Communication_Protocol = %s,
                Binding =%s,
                Time = %s
                WHERE 
                DeviceID = %s'''
            try:
                async with conn.cursor() as cur:
                    await cur.execute(query,(RaspberryPi_ID,Status,Status_Detail,Status_Desc,Communication_Protocol,Binding,Time,DeviceID))
                    await conn.commit()
                    logger.info(f"Entry {DeviceID} has been updated in devices table)")
            except Exception as e:
                logger.exception("Could not update devices table, tracback shown below\n{e}")
        else:
            logger.exception("Could not insert new device into devices table, tracback shown below")

    #Close the connection
    finally:
        try:
            await cur.close()
        except UnboundLocalError:
            pass


##query_all_values##
# The purpose of this function is to query the meter_values table for the most recent meter read:w
#+----------------------+--------------+------+-----+----------------------+-------------------+
#| Field                | Type         | Null | Key | Default              | Extra             |
#+----------------------+--------------+------+-----+----------------------+-------------------+
#| Meter_ID             | varchar(255) | NO   | PRI | NULL                 |                   |
#| Voltage              | float        | YES  |     | NULL                 |                   |
#| Voltage_Units        | varchar(255) | YES  |     | Volts                |                   |
#| Current              | float        | YES  |     | NULL                 |                   |
#| Current_Units        | varchar(255) | YES  |     | Amps                 |                   |
#| Power                | float        | YES  |     | NULL                 |                   |
#| Power_Units          | varchar(255) | YES  |     | kW                   |                   |
#| Reactive_Power       | float        | YES  |     | NULL                 |                   |
#| Reactive_Power_Units | varchar(255) | YES  |     | kVAR                 |                   |
#| Apparent_Power       | float        | YES  |     | NULL                 |                   |
#| Apparent_Power_Units | varchar(255) | YES  |     | kVA                  |                   |
#| Power_Factor         | float        | YES  |     | NULL                 |                   |
#| Time_MTCP            | timestamp(3) | YES  |     | NULL                 |                   |
#| Time_SQL             | timestamp(3) | NO   |     | CURRENT_TIMESTAMP(3) | DEFAULT_GENERATED |
#+----------------------+--------------+------+-----+----------------------+-------------------+
#Inputs:
#    conn - A database connection 
#    IP   - The IP address of the meter that is to be queried  
#Return:
#   Voltage
#   Current
#   Power
#   Reactive Power 
#   Apparent Power
#   Power Factor
async def query_all_values(conn,IP):
    try:
        query = ''' select Voltage, Current, Power, Reactive_Power, Apparent_Power, Power_Factor 
                    from meter_values where Meter_ID = %s   
        '''
        async with conn.cursor() as cur:
            await cur.execute(query,(IP))
            await conn.commit()
    except Exception as e:
        logger.exception(e)
    else:
        result = (await cur.fetchone())
        logger.info(f"Succesful read")
        return result[0], result[1], result[2], result[3], result[4], result[5]
    finally:
        await cur.close()        



##Update_AllValues##
# The purpose of this function is to update the all_values table and the meter_values table
# The all values table keeps a record of historical meter readings, the meter_values table keeps
# a record of the most recent readings  
# The layout of the all_values table is:
#+----------------------+--------------+------+-----+----------------------+-------------------+
#| Field                | Type         | Null | Key | Default              | Extra             |
#+----------------------+--------------+------+-----+----------------------+-------------------+
#| ID                   | int          | NO   | PRI | NULL                 | auto_increment    |
#| Voltage              | float        | YES  |     | NULL                 |                   |
#| Voltage_Units        | varchar(255) | YES  |     | Volts                |                   |
#| Current              | float        | YES  |     | NULL                 |                   |
#| Current_Units        | varchar(255) | YES  |     | Amps                 |                   |
#| Power                | float        | YES  |     | NULL                 |                   |
#| Power_Units          | varchar(255) | YES  |     | kW                   |                   |
#| Reactive_Power       | float        | YES  |     | NULL                 |                   |
#| Reactive_Power_Units | varchar(255) | YES  |     | kVAR                 |                   |
#| Apparent_Power       | float        | YES  |     | NULL                 |                   |
#| Apparent_Power_Units | varchar(255) | YES  |     | kVA                  |                   |
#| Power_Factor         | float        | YES  |     | NULL                 |                   |
#| Meter_ID             | varchar(255) | YES  |     | NULL                 |                   |
#| Time_MTCP            | timestamp(3) | YES  |     | NULL                 |                   |
#| Time_SQL             | timestamp(3) | NO   |     | CURRENT_TIMESTAMP(3) | DEFAULT_GENERATED |
#+----------------------+--------------+------+-----+----------------------+-------------------+
#The layout of the meter_values table:
#+----------------------+--------------+------+-----+----------------------+-------------------+
#| Field                | Type         | Null | Key | Default              | Extra             |
#+----------------------+--------------+------+-----+----------------------+-------------------+
#| Meter_ID             | varchar(255) | NO   | PRI | NULL                 |                   |
#| Voltage              | float        | YES  |     | NULL                 |                   |
#| Voltage_Units        | varchar(255) | YES  |     | Volts                |                   |
#| Current              | float        | YES  |     | NULL                 |                   |
#| Current_Units        | varchar(255) | YES  |     | Amps                 |                   |
#| Power                | float        | YES  |     | NULL                 |                   |
#| Power_Units          | varchar(255) | YES  |     | kW                   |                   |
#| Reactive_Power       | float        | YES  |     | NULL                 |                   |
#| Reactive_Power_Units | varchar(255) | YES  |     | kVAR                 |                   |
#| Apparent_Power       | float        | YES  |     | NULL                 |                   |
#| Apparent_Power_Units | varchar(255) | YES  |     | kVA                  |                   |
#| Power_Factor         | float        | YES  |     | NULL                 |                   |
#| Time_MTCP            | timestamp(3) | YES  |     | NULL                 |                   |
#| Time_SQL             | timestamp(3) | NO   |     | CURRENT_TIMESTAMP(3) | DEFAULT_GENERATED |
#+----------------------+--------------+------+-----+----------------------+-------------------+
#Inputs:
#   regs - A dictionary with the keys "Volts","Current","kW","kvar","kVA","PF" for values 
#   IP   - The IP of the meter 
#   time - A time stamp of when the modbus read occured 
async def update_all_values(regs,IP,time,conn):
    ##Try to insert in all_values table
    try:
        query = ''' INSERT INTO all_values(Voltage,Current,Power,Reactive_Power,Apparent_Power,Power_Factor,Meter_ID,Time_MTCP)
                 VALUES(%s,%s,%s,%s,%s,%s,%s,%s) '''

        async with conn.cursor() as cur:
            await cur.execute(query,(regs['Volts'],regs['Current'],regs['kW'],regs['kvar'],regs['kVA'],regs['PF'],IP,time))
            await conn.commit()
            logger.info(f"New entry in the all_values table for {IP}")

    except Exception as e:
        logger.exception(f"Error in trying to log new entry in all_values tbale for meter {IP}")
    ##Try to insert into the meter_values table
    try:
        query = ''' INSERT INTO meter_values(Meter_ID,Voltage,Current,Power,Reactive_Power,Apparent_Power,Power_Factor,Time_MTCP)
                 VALUES(%s,%s,%s,%s,%s,%s,%s,%s) '''
        async with conn.cursor() as cur:
            await cur.execute(query,(IP,regs['Volts'],regs['Current'],regs['kW'],regs['kvar'],regs['kVA'],regs['PF'],time))
            await conn.commit()
            logger.info(f"Entry created for meter {IP} in the meter_values table")
    except Exception as e:
        code, message = e.args
        if code == 1062:
            logger.warning(f"Entry {IP} exists in meter_Values table, attempting to update entry")
            query = '''UPDATE meter_values
                SET 
                Voltage =%s,
                Current= %s,
                Power = %s,
                Reactive_Power =%s,
                Apparent_Power =%s,
                Power_Factor = %s,
                Time_MTCP =%s,
                Time_SQL = %s
                WHERE 
                Meter_ID = %s'''
            try:
                async with conn.cursor() as cur:
                    await cur.execute(query,(regs['Volts'],regs['Current'],regs['kW'],regs['kvar'],regs['kVA'],regs['PF'],time,datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'),IP))
                    await conn.commit()
                    logger.info(f"Entry {IP} has been updated in meter_values table)")
            except Exception as e:
                logger.exception(f"Could not update meter_values table with {IP}, tracback shown below")
        else:
            logger.exception(f"Could not insert entry {IP} into meter_values table\n{e}")
    else:
        logger.info(f"New entry from {IP} in the all values table")
    finally:
        await cur.close()

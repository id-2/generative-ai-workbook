"""
Main script for application

"""
import os
import sys
import dotenv
import autogen
import argparse

# sys.path.append('./') 
dotenv.load_dotenv()

from agents import ad #(safe_get, response_parser, prompt, add_cap_ref)  
# from .api import *
# from .config import *
# from .data.dictionaries import *

from data.db import PostgresManager
from utils.agent_utils import (get_config)


DB_URL = os.environ.get("POSTGRES_CONNECTION_URL")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

def main():
    # parse prompt param using arg parse
    parser = argparse.ArgumentParser()
    parser.add_argument("prompt", help="The prompt for the AI")
    args = parser.parse_args()

    # get autogen config list
    config_list = get_config(model_type='gpt-4', dotenv_path='../../../.env')

    # connect to db using with statement and create a db_manager
    with PostgresManager() as db:
        db.connect_with_url(DB_URL)
        # users_table = db.try_query()
        users_table = db.get_all(table_name="patients")
        print("users_table", users_table)

    # call db_manager.get_table_definition_for_prompt () to get tables in prompt ready form
    table_definitions = db.get_table_definitions_for_prompt()

    # create two blank calls to 1lm.add_cap_ref() that update our current prompt passed in from cli
    prompt = ad.add_cap_ref(args.prompt, "Please provide the SQL query for the following table definitions:", "TABLE DEFINITIONS", table_definitions)
    prompt = ad.add_cap_ref(prompt, "Please provide the SQL query for the following table definitions:", "TABLE DEFINITIONS", table_definitions)

    # call llm.prompt to get a prompt_ response variable
    prompt_response = ad.prompt(prompt)

    # parse sql response from prompt_response using SQL_QUERY_DELIMITER '---------'
    sql_query = prompt_response.split('---------')[1].strip()

    # call db_manager. run_sql() with the parsed sql
    result = db.run_sql(sql_query)
    print(result)

if __name__ == "__main__":
    main()

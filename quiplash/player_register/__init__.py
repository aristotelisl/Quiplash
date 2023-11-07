import logging
import json
import os
import uuid
from azure.cosmos import CosmosClient
from azure.functions import HttpRequest, HttpResponse, Document, Out
from azure.cosmos.exceptions import CosmosResourceExistsError

MyCosmos = CosmosClient.from_connection_string(os.environ['AzureCosmosDBConnectionString'])
QuiplashDBProxy = MyCosmos.get_database_client(os.environ['Database'])
PlayerContainerProxy = QuiplashDBProxy.get_container_client(os.environ['PlayerContainer'])
    
def main(req: HttpRequest) -> HttpResponse:

    req_body = req.get_json()
    logging.info('We are requested to register a player from this {}'.format(req_body))

    username = req_body.get('username')
    password = req_body.get('password')
    
    # query for obtaining players (if they exist) with this specific username
    query = f"SELECT * FROM c WHERE c.username = '{username}'"
    existing_users = list(PlayerContainerProxy.query_items(query, enable_cross_partition_query=True))

    try:
        result=False
        msg=""
        if existing_users:
            msg = "Username already exists"
        elif len(username) < 4 or len(username) > 14:
            msg="Username less than 4 characters or more than 14 characters"
        elif len(password) < 10 or len(password) > 20:
            msg="Password less than 10 characters or more than 20 characters"
        else:     
            # create json for new user 
            user = {
                "id": str(uuid.uuid4()),
                "username" : username,
                "password": password,
                "games_played": 0,
                "total_score": 0
            }
            # add user to the database
            try:
                PlayerContainerProxy.create_item(user)
                result = True
                msg = "OK"
            except CosmosResourceExistsError:
                msg = "Username already exists"
                
        return HttpResponse(json.dumps({"result": result, "msg": msg }))
    
    except Exception as err:
        logging.error(err)
        return HttpResponse("Something unexpected and bad happened during insertion, look at the server log",status_code=500)
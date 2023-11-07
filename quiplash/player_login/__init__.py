import logging
import json
import os
from azure.cosmos import CosmosClient
from azure.functions import HttpRequest, HttpResponse

MyCosmos = CosmosClient.from_connection_string(os.environ['AzureCosmosDBConnectionString'])
QuiplashDBProxy = MyCosmos.get_database_client(os.environ['Database'])
PlayerContainerProxy = QuiplashDBProxy.get_container_client(os.environ['PlayerContainer'])

def main(req: HttpRequest) -> HttpResponse:
    
    req_body = req.get_json()
    logging.info('We are requested to login a player from this {}'.format(req_body))
    
    username = req_body.get('username')
    password = req_body.get('password')

    try:
        result = False
        # query for obtaining players (if they exist) with this specific username
        query = f"SELECT * FROM c WHERE c.username = '{username}'"
        items = list(PlayerContainerProxy.query_items(query, enable_cross_partition_query=True))
        
        # if player exists, proceed to check for password, otherwise incorrect username
        if len(items) == 1:
            user = items[0]
            
            # check password
            if user['password'] == password:
                result = True
                msg = "OK"
            else:
                msg = "Username or password incorrect"
        else:
            msg = "Username or password incorrect"
            
        return HttpResponse(json.dumps({"result": result, "msg": msg }))
    
    except Exception as err:
        logging.error(err)
        return HttpResponse("Something unexpected and bad happened, look at the server log",status_code=500)
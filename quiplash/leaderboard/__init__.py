import logging
import json
import os
from azure.cosmos import CosmosClient
from azure.functions import HttpRequest, HttpResponse

MyCosmos = CosmosClient.from_connection_string(os.environ['AzureCosmosDBConnectionString'])
QuiplashDBProxy = MyCosmos.get_database_client(os.environ['Database'])
PlayerContainerProxy = QuiplashDBProxy.get_container_client(os.environ['PlayerContainer'])


def main(req: HttpRequest) -> HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')
    
    req_body = req.get_json()
    top = req_body.get('top')
    
    try:
        result = []
        # read all items from player container
        players = list(PlayerContainerProxy.read_all_items())
        
        # loop through all players
        for player in players:
            # filter out only the information we want from each player
            item = {
                "username": player.get("username"),
                "games_played": player.get("games_played"),
                "total_score": player.get("total_score")
            }
            result.append(item)

        # sort the players based on specification requirements 
        result.sort(key=lambda x: (-x["total_score"], x["games_played"], x["username"]))
        # get the top players
        result = result[:top]
    
        return HttpResponse(json.dumps(result))
    except Exception as err:
        logging.error(err)
        return HttpResponse("Something unexpected and bad happened, look at the server log",status_code=500)
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
    logging.info('We are requested to update a player from this {}'.format(req_body))
    
    username = req_body.get('username')
    add_to_games_played = req_body.get('add_to_games_played')
    add_to_score = req_body.get('add_to_score')
        
    try:
        result = False
        # query for obtaining players (if they exist) with this specific username
        query = f"SELECT * FROM c WHERE c.username = '{username}'"
        items = list(PlayerContainerProxy.query_items(query, enable_cross_partition_query=True))
    
        if len(items) == 1:
            if (add_to_games_played < 0):
                msg = "add_to_games_played cannot be a negative value"
            elif (add_to_score < 0):
                msg = "add_to_score cannot be a negative value"
            else:
                user = items[0]
                # add games and score count
                newGamesPlayed = user['games_played'] + add_to_games_played
                newTotalScore = user['total_score'] + add_to_score
                # overwrite games_played and total_score with the new values
                PlayerContainerProxy.replace_item(item=user["id"], body={"id": user["id"], "username": user["username"], "password": user["password"], "games_played": newGamesPlayed, "total_score": newTotalScore})

                result = True
                msg = "OK"
        else:
            msg = "Player does not exist"
            
        return HttpResponse(json.dumps({"result": result, "msg": msg }))
            
    except Exception as err:
        logging.error(err)
        return HttpResponse("Something unexpected and bad happened, look at the server log",status_code=500)
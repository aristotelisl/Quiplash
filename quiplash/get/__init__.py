import logging
import json
import os
from azure.cosmos import CosmosClient
from azure.functions import HttpRequest, HttpResponse

MyCosmos = CosmosClient.from_connection_string(os.environ['AzureCosmosDBConnectionString'])
QuiplashDBProxy = MyCosmos.get_database_client(os.environ['Database'])
PlayerContainerProxy = QuiplashDBProxy.get_container_client(os.environ['PlayerContainer'])
PromptContainerProxy = QuiplashDBProxy.get_container_client(os.environ['PromptContainer'])

def main(req: HttpRequest) -> HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    req_body = req.get_json()

    usernames = req_body.get('players')
    language = req_body.get('language')
    
    try:
        result = []
        for username in usernames:
            # get all prompts from specified username
            query = f"SELECT * FROM c WHERE c.username = '{username}'"
            itemsPrompts = list(PromptContainerProxy.query_items(query, enable_cross_partition_query=True))
            for item in itemsPrompts:
                for text_entry in item['texts']:
                    # check it is the language we want
                    if text_entry['language'] == language:
                        # append item for our response
                        result.append({
                            'id': item['id'],
                            'text': text_entry['text'],
                            'username': username
                        })
                                        
        return HttpResponse(json.dumps(result))
                        
    except Exception as err:
        logging.error(err)
        return HttpResponse("Something unexpected and bad happened, look at the server log",status_code=500)
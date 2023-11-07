import logging
import json
import os
import re
from azure.cosmos import CosmosClient
from azure.functions import HttpRequest, HttpResponse

MyCosmos = CosmosClient.from_connection_string(os.environ['AzureCosmosDBConnectionString'])
QuiplashDBProxy = MyCosmos.get_database_client(os.environ['Database'])
PlayerContainerProxy = QuiplashDBProxy.get_container_client(os.environ['PlayerContainer'])
PromptContainerProxy = QuiplashDBProxy.get_container_client(os.environ['PromptContainer'])

def main(req: HttpRequest) -> HttpResponse:

    req_body = req.get_json()
    logging.info('We are requested to delete a prompt from this {}'.format(req_body))
    
    try:
        result = False
        
        # check whether req_body contains player or word to delete, act accordingly
        if "player" in req_body:
            username = req_body.get('player')
            # get all prompts with requested username
            query = f"SELECT * FROM c WHERE c.username = '{username}'"
            itemsPrompts = list(PromptContainerProxy.query_items(query, enable_cross_partition_query=True))
            
            counter = len(itemsPrompts)
            if len(itemsPrompts) >= 1:
                # loop through selected prompts and delete them
                for item in itemsPrompts:
                    PromptContainerProxy.delete_item(item, item.get('username'))
                    
            result = True
            msg = f"{counter} prompts deleted"       
        elif "word" in req_body:
            word = req_body.get('word')
            counterWord = 0
            # loop through all prompts
            for item in PromptContainerProxy.read_all_items():
                prompt_texts = [text['text'] for text in item.get('texts', [])]
                # delete prompts with that exact specific word
                if any(re.search(rf'\b{re.escape(word)}\b', text) for text in prompt_texts):
                    PromptContainerProxy.delete_item(item, item.get('username'))
                    counterWord = counterWord + 1
                    result = True
                    msg = f"{counterWord} prompts deleted"
                
            if counterWord == 0:
                msg = "No change in the collection" 
                
        return HttpResponse(json.dumps({"result": result, "msg": msg }))
    except Exception as err:
        logging.error(err)
        return HttpResponse("Something unexpected and bad happened, look at the server log",status_code=500)
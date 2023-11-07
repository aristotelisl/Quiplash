import logging
import json
import os
import requests
import uuid
from azure.cosmos import CosmosClient
from azure.functions import HttpRequest, HttpResponse
from azure.ai.textanalytics import TextAnalyticsClient
from azure.core.credentials import AzureKeyCredential
from langdetect import detect, DetectorFactory, detect_langs

MyCosmos = CosmosClient.from_connection_string(os.environ['AzureCosmosDBConnectionString'])
QuiplashDBProxy = MyCosmos.get_database_client(os.environ['Database'])
PlayerContainerProxy = QuiplashDBProxy.get_container_client(os.environ['PlayerContainer'])
PromptContainerProxy = QuiplashDBProxy.get_container_client(os.environ['PromptContainer'])

TextTranslationKey = os.environ['TranslationKey']
Endpoint = os.environ['TranslationEndpoint']

def main(req: HttpRequest) -> HttpResponse:

    req_body = req.get_json()
    logging.info('We are requested to create a prompt for a player from this {}'.format(req_body))

    text = req_body.get('text')
    username = req_body.get('username')
    
    try:
        result = False
        query = f"SELECT * FROM c WHERE c.username = '{username}'"
        items = list(PlayerContainerProxy.query_items(query, enable_cross_partition_query=True))
    
        if len(items) == 1:
            if (len(text) < 15 or len(text) > 80):
                msg = "Prompt less than 15 characters or more than 80 characters"
            else:
                # call function to detect language of text
                detected_language = detect_language(text)
                # set the list of supported languages for quiplash
                target_languages = ['en', 'es', 'it', 'sv', 'ru', 'id', 'bg', 'zh-Hans']

                supportedLang = False
                
                #check detected language is one of the supported languages
                for language in target_languages:
                    if detected_language == language:
                        supportedLang = True
                        
                if supportedLang:
                    # call function to translate our language, parse the text and target_languages
                    translated_texts = translate_text(text, target_languages)
                    prompt_texts = []
                    # loop through all languages and append them to a list
                    for language, translated_text in translated_texts.items():
                        prompt_texts.append({"language": language, "text": translated_text})
                    # create json for our prompt
                    prompt = {
                        "id": str(uuid.uuid4()),
                        "username" : username,
                        "texts": prompt_texts
                    }
                    PromptContainerProxy.create_item(prompt)
                    result = True
                    msg = "OK"
                else:
                    msg = "Unsupported language"
        else:
            msg = "Player does not exist"
            
        return HttpResponse(json.dumps({"result": result, "msg": msg }))
            
    except Exception as err:
        logging.error(err)
        return HttpResponse("Something unexpected and bad happened, look at the server log",status_code=500)

# use code snippets from https://learn.microsoft.com/en-us/azure/ai-services/translator/quickstart-text-rest-api?tabs=python to translate our text
def translate_text(text, target_languages):
    translation_results = {}

    for language in target_languages:
        headers = {
            'Ocp-Apim-Subscription-Key': TextTranslationKey,
            'Ocp-Apim-Subscription-Region': 'uksouth',
            'Content-type': 'application/json',
        }

        body = [{'text': text}]

        params = f"api-version=3.0&to={language}"
        translate_url = f"{Endpoint}/translate?{params}"

        response = requests.post(translate_url, headers=headers, json=body)

        if response.status_code == 200:
            result = response.json()
            translated_text = result[0]['translations'][0]['text']
            translation_results[language] = translated_text
        else:
            translation_results[language] = f"Translation failed for {language}"

    return translation_results

# def authenticate_client():
    ta_credential = AzureKeyCredential(TextTranslationKey)
    text_analytics_client = TextAnalyticsClient(
            endpoint=Endpoint, 
            credential=ta_credential)
    return text_analytics_client

# def detect_language(text, client):

    documents=[text]
    response = client.detect_language(documents = documents)[0]
    
    detected_language = response.primary_language.language
    confidence = response.primary_language.score

    return detected_language, confidence

# use langdetect library to detect the input language (azure ai text analytics wouldn't work for me)
def detect_language(text):
    try:
        results = detect(text)
    
        return results
    except Exception as e:
        return None, str(e)
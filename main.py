from googleapiclient.discovery import HttpError, build  
from google.oauth2.credentials import Credentials 
from google_auth_oauthlib.flow import InstalledAppFlow 


import json 
import os
import time 


class CredentialError(Exception):
    pass

class MessageError(Exception):
    pass

class NoMessagesFound(Exception):
    pass

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify"
]#SCOPES generales

#OBTENCIÓN DE CREDENCIALES Y RECURSOS
def get_credentials ():
    if os.path.exists("Token.json"):#Obtiene las credenciales en caso de que Token.json exista
        credentials = Credentials.from_authorized_user_file(
            "Token.json",
            SCOPES
        )
    else:
        try:#Crea el archivo Token.json a partir del archivo preexistente credenciales.json
            flow=InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES) #El archivo credentials.json contiene la configuaración del cliente OAuth qeu identifica el programa ante google y permite que haya una comunicación con la API de gmail
        except Exception as e:
            print(e)
            raise CredentialError("Problemas con el archivo credentials.json")
        credentials = flow.run_local_server()
        archivo_token=open("Token.json", "w")
        archivo_token.write(credentials.to_json())
        archivo_token.close()
    return credentials

def cliente_gmail(credentials):
    cliente = build(
        "gmail",
        "v1",
        credentials=credentials
    )
    return cliente

def recursos (cliente):
    usuario = cliente.users()
    msg = usuario.messages()
    lbls=usuario.labels()
    return msg, lbls #Recursos: mensajes y etiquetas

def get_msg(msg,ID, user="me"):
    try:
        missatge=msg.get(userId=user, id=ID).execute()#Obtención de un único mensaje a través de su ID
    except HttpError as e:
        if e.resp.status == 404:
            raise MessageError("No hay mensajes que coincidan con esta ID")
        else:
            error = json.loads(e.content)
            print(json.dumps(error, indent=4))
            raise MessageError("Problemas con el mensaje especificado")
    return missatge

#ETIQUETAJE
def etiquetar (msg, lbls, user="me"):

    organizer={ #Diccionario en el que se especifican los filtros. En keywords se buscan en el subject del mensaje y se permiten frases
        "nombre_etiqueta_1": {
            "id":None,
            "keywords": ["Palabra", "Palabra1 y Palabra2"],
            "remitentes":["ejemplo@correo.com"]
            },
        "nombre_etqueta_2":  {
            "id":None,
            "keywords": [],
            "remitentes":[]
        }
    }
    query=[]
    Labels=[]
    for lb in organizer:
        Labels.append(f"-label:{lb}") #los mensjaes que ya tienen alguna de las etiquetas se consideran ya clasificados y decidimos saltarlos

        for kw in organizer[lb]["keywords"]: #añadimos a la query las palabres o frases clave especificadas en keywords
             query.append(f"subject:{kw}")

        for n in organizer[lb]["remitentes"]: #añadimos los remitentes que nos interesan
            query.append(f"from:{n}")
            query.append(f"to:{n}")#también filtramos los mensjaes tales que los destinatarios són los remitentes especificados, para detectar conversaciones bidireccionales

    query=" OR ".join(query)
    Labels=" ".join(Labels)
    q=f"-is:starred {Labels} {{{query}}}" #obviamos también los mensajes destacados

    #obtenemos la lista de mensajes esepcificados y etiquetas existentes
    llista_missatges = msg.list(userId=user,q=q).execute()
    llista_labels = lbls.list(userId=user).execute()

    #Creamos las etiquetas de organizer que no existan
    for lb in organizer:
        for l in llista_labels["labels"]:
            if l["name"]==lb:
                organizer[lb]["id"]=l["id"]
                break
        if organizer[lb]["id"] is None:
                nova_lbl=lbls.create(userId=user, body={"name": lb}).execute()
                organizer[lb]["id"]=nova_lbl["id"]
                print(f"Se ha creado la etiqueta {lb}")

    total=llista_missatges["resultSizeEstimate"]
    if total == 0:
        raise NoMessagesFound("No hay mensajes que respondan a la query.")
    cont=0#contador de mensajes
    while True:
        for m in llista_missatges.get("messages", []):

            a=msg.get(userId=user, id=m["id"], format="metadata", metadataHeaders=["Subject", "From"]).execute()

            label_ids_to_add=set()#lugar donde almacenamos las id's de las labels a añadir. Queremos ahorrarnos duplicados por eso lo hacemos en un set
            asunto=None

            #obtenemos los headers respeto los que filtramos en organizer
            for head in a["payload"]["headers"]:
                if head["name"] == "Subject":
                    asunto = head["value"]
                elif head["name"] == "From":
                    remitente = head["value"]

            #etiquetaje teniendo en cuenta el subject
            if asunto is not None:
                for lb in organizer:
                    for kw in organizer[lb]["keywords"]:    
                        if " " in kw:
                            try:
                                if kw.lower() in asunto.lower() and organizer[lb]["id"] not in a["labelIds"]:
                                    label_ids_to_add.add(organizer[lb]["id"])
                            except KeyError as e:
                                print(f"Atención:{e}. El mensaje {m["id"]} no tiene el contenedor de labelIds.", end="")
                                if kw.lower() in asunto.lower():
                                    label_ids_to_add.add(organizer[lb]["id"])
                                    print(f": Se ha etiquetado correctamente")
                                print("\n")
                                
                        else:
                            paraules=asunto.lower().split()
                            try:
                                if kw.lower() in paraules and organizer[lb]["id"] not in a["labelIds"]:
                                    label_ids_to_add.add(organizer[lb]["id"])
                            except KeyError as e:
                                print(f"Atenció, KeyError:{e}. El mensaje {m["id"]} no tiene el contenedor labelIds.", end="")
                                if kw.lower() in paraules:
                                    label_ids_to_add.add(organizer[lb]["id"])
                                    print(f": Se ha etiquetado correctamente")
                                print("\n")
            #etiquetaje segun el remitente
            for lb in organizer:
                for sd in organizer[lb]["remitentes"]:
                    try:
                        if sd in remitente and organizer[lb]["id"] not in a["labelIds"]:
                            label_ids_to_add.add(organizer[lb]["id"])
                    except KeyError as e:
                        print(f"Atenció, KeyError: {e}, missatge: {m["id"]}.", end="")
                        if sd in remitente:
                            label_ids_to_add.add(organizer[lb]["id"])
                            print(f": El mensaje del remitente {sd} no tiene el contenedor de labelIds pere se ha etiquetado correctamente")
                        print("\n") 

            #añadimos las etiquetas especificadas
            if label_ids_to_add:
                label_ids_to_add = list(label_ids_to_add)
                msg.modify(
                    userId=user, 
                    id=m["id"],
                    body={
                        "addLabelIds": label_ids_to_add,
                        "removeLabelIds": ["INBOX"]
                        }
                    ).execute()
            cont+=1
            if cont==prog +50:
                prog+=50
                print(f"\r{cont}", end="")

        #control de pagina
        TokenPagina = llista_missatges.get("nextPageToken") 
        if TokenPagina is None:
            break
        llista_missatges=msg.list(userId=user, pageToken=TokenPagina,q=q).execute()
    print(f"\ntotal:{cont}")

def safata_entrada_scan(msg, user="me"):
    llista_missatges = msg.list(userId=user,q="label:INBOX").execute()#obtenemos lista mensajes que esten en la bandeja entrada

    total=llista_missatges["resultSizeEstimate"]
    if total == 0:
        raise NoMessagesFound("No hay mensajes que respondan a la query.")
    cont=0
    while True:#quitamos la etiqueta bandeja entrada
        for m in llista_missatges.get("messages", []):
            a=msg.get(userId=user, id=m["id"], format="metadata", metadataHeaders=["Subject", "From"]).execute()
            try:
                for lb in  a["labelIds"]:
                    if lb !="INBOX":
                        msg.modify(
                            userId=user, 
                            id=m["id"],
                            body={
                                "removeLabelIds": ["INBOX"]
                                }
                            ).execute()
                        break
            except KeyError as e:
                 print(f"Atenció, KeyError:{e}. El missatge {m["id"]} no te el contenidor de labelIds. S'ha omés") 

            cont+=1
            if cont%50==0:
                print(f"\r{cont}", end="")

        TokenPagina = llista_missatges.get("nextPageToken") #control de pagina
        if TokenPagina is None:
            break
        llista_missatges=msg.list(userId=user, pageToken=TokenPagina,q="label:INBOX").execute()
    print(f"\ntotal:{cont}")

def rmv_label(lbls,lbl_name, remitent , msg, user="me"):

    query=f"from:{remitent}"
    q=f"-is:starred label:{lbl_name} {{{query}}}" #creamos la query que nos devuelva los mensajes con la etiqueta especificada y el remitente especificado. Evitamos los destacados
    
    llista_missatges = msg.list(userId=user,q=q).execute()
    llista_labels = lbls.list(userId=user).execute()

    total=llista_missatges["resultSizeEstimate"]
    if total == 0:
         raise NoMessagesFound("No hay mensajes que respondan a la query.")

    lbl_id=None

    for l in llista_labels["labels"]: #obtenemos id etiqueta
        if l["name"].lower()==lbl_name.lower():
            lbl_id=l["id"]
            break
    if lbl_id is None:
        raise Exception("Etiqueta introducida no encontrada")
    
    cont=0
    while True: #desequitetamos todos los mensajes especificados
        for m in llista_missatges.get("messages", []):
            msg.modify(
                userId=user, 
                id=m["id"],
                body={
                    "removeLabelIds": [lbl_id]
                    }
                ).execute()
            cont+=1
            if cont % 50==0:
                print(f"\r{cont}", end="")       
        TokenPagina = llista_missatges.get("nextPageToken") #control de pagina 
        if TokenPagina is None:
            break
        llista_missatges=msg.list(userId=user, pageToken=TokenPagina,q=q).execute()
    print(f"\ntotal:{cont}")

#ENVIAR MENSAJES A LA PAPELERA
def marcar_brossa (msg,lbls, user="me"):
    paperera={ #diccionario con los remitentes que queremos que sean marcados como basura, o con ciertas palabras o frases clave en el Subject
        "remitentes": [
            "ejemplo1@correo.com"
            ],
        "keywords": []
    }

    whitelist={ #diccionario que indica los remitentes que seran exemptos de ser considerados candidatos a basura
        "remitentes":["ejemplo2@correo.com"]
    }

    #creación de la query segun los diccionarios whitelist y paperera
    query=[]
    queryW=[]
    for n in whitelist["remitentes"]:
            queryW.append(f"-from:{n}")
    for n in paperera["remitentes"]:
        query.append(f"from:{n}")
    for n in paperera["keywords"]:
        query.append(f"subject:{n}")
    query=" OR ".join(query)
    queryW=" ".join(queryW)
    q=f"-is:starred -label:Papelera {queryW} {{{query}}}" #obviamos también los mensajes destacados

    #obtención de los mensajes y etiquetas
    llista_missatges = msg.list(userId=user,q=q).execute()
    llista_labels = lbls.list(userId=user).execute()

    #si la etiqueta papelera no existe, la creamos. En caso contrario obtenemos su id
    Check=1
    for l in llista_labels["labels"]:
        if l["name"]=="Papelera":
            etiqueta_brossa=l
            Check=0
            break
    if Check:
        etiqueta_brossa=lbls.create(userId=user, body={"name": "Papelera"}).execute()#guardem el resultat per guardar la id
        print(f"S'ha creat la etiqueta Papelera")

    total=llista_missatges["resultSizeEstimate"]
    if total == 0:
        raise NoMessagesFound("No hay mensajes que respondan a la query.")

    cont=0

    while True:
        for m in llista_missatges.get("messages",[]):
            msg.modify(userId=user, id=m["id"],body={"addLabelIds": [etiqueta_brossa["id"]]}).execute()
            cont+=1
            if cont%50==0:
                print(f"\r{cont}", end="")

        TokenPagina = llista_missatges.get("nextPageToken") #control de pagina
        if TokenPagina is None:
            break
        llista_missatges=msg.list(userId=user, pageToken=TokenPagina,q=q).execute()
    print(f"\ntotal:{cont}")

def enviar_brossa(msg, user="me"):
    #función complementaroa a marcar_brossa
    
    q="label:Papelera"
    llista_missatges = msg.list(userId=user,q=q).execute() #lista mensajes con la etiqueta Papelera
    total=llista_missatges["resultSizeEstimate"]
    if total == 0:
        raise NoMessagesFound("No hay mensajes que respondan a la query.")
    cont=0
    while True: #se aplica trash() a los mensajes de dentro la etiqueta 
        for m in llista_missatges.get("messages", []):
            msg.trash(userId=user,id=m["id"]).execute()
            cont+=1
            if cont%50==0:
                print(f"\r{cont}", end="")
        TokenPagina = llista_missatges.get("nextPageToken") #control de pagina
        if TokenPagina is None:
            break
        llista_missatges=msg.list(userId=user, pageToken=TokenPagina,q=q).execute()
    print(f"\ntotal:{cont}")


#FUNCIO PER CANVIAR D'USUARI
def reset_user ():
    if os.path.exists("Token.json"):
        os.remove("Token.json")
        print("Se ha eliminado Token.json. Inicia la sesion con otro usuario autorizado")

if __name__=="__main__":
    
    credentials=get_credentials()
    cliente=cliente_gmail(credentials)
    msg,lbls=recursos(cliente)
   
    etiquetar(cliente,msg, lbls)
    marcar_brossa(msg, lbls)
    enviar_brossa(msg)
            

    


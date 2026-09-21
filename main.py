from googleapiclient.discovery import HttpError, build  
from google.oauth2.credentials import Credentials 
from google_auth_oauthlib.flow import InstalledAppFlow 

from googleapiclient.http import BatchHttpRequest

import json 
import os
import time 

class CredentialError(Exception):
    pass

class MessageError(Exception):
    pass

class NoMessagesFound(Exception):
    pass

class QuoataAssolida (Exception):
    pass

class UnitatsUsades:#control de las uniadades por minuto
    LIMIT=6000
    TEMPS=60

    def __init__(self, t0=0, unitats=0):
        self.unitats=unitats
        self.t0=t0
        self.t1=t0
    
    def afegir (self,n):
        self.t1=time.monotonic()
        if self.unitats==0:
            self.t0=self.t1
        if self.t1-self.t0>=self.TEMPS:
            self.unitats=0
        elif self.unitats+n > self.LIMIT:#Els increments venen de messages.list, messages.get, messages.modify, messages.trash, labels.list, labels.create i augmente 1,5 i 20 unitats
            self.unitats=0
            return 0
        self.unitats += n
        return 1
    def times (self):
        if self.t1-self.t0 != 0:
            print(f"Unitats: {self.unitats}")
            print(f"\nutlim afegir: {int(self.t1)}s")
            print(f"ultim inici: {int(self.t0)}s")
            print(f"Interval: {int(self.t1-self.t0)}s, falten {int(60-self.t1+self.t0)}s pel reinici")
        else:
            print(f"Unitats: {self.unitats}")
            print(f"t0 i t1={int(self.t1)}s")

Unitats=UnitatsUsades()

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify"
]

#OBTENCIÓN DE CREDENCIALES Y RECURSOS
def get_credentials ():
    if os.path.exists("Token.json"):#Obtiene las credenciales en caso de que Token.json exista
        credentials = Credentials.from_authorized_user_file(
            "Token.json",
            SCOPES
        )
    else:
        try:#Crea el archivo Token.json a partir del archivo preexistente credenciales.json
            flow=InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)#El archivo credentials.json contiene la configuaración del cliente OAuth qeu identifica el programa ante google y permite que haya una comunicación con la API de gmail
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
       if Unitats.afegir(20):
            missatge=msg.get(userId=user, id=ID).execute()#Obtención de un único mensaje a través de su ID
       else:
            raise QuoataAssolida ("Se ha alcanzado la quota de unidades por minuto.")
    except HttpError as e:
        if e.resp.status == 404:
            raise MessageError("No hay mensajes que coincidan con esta ID")
        else:
            error = json.loads(e.content)
            print(json.dumps(error, indent=4))
            raise MessageError("Problemas con el mensaje especificado")
    return missatge

#ETIQUETAJE
def etiquetar (cliente, msg, lbls, user="me"):
    try: #obtenemos el organizer a través de los archivos .txt
        with open("organizer.txt", "r", encoding="utf-8") as f: 
            organizer=json.load(f)
    except json.JSONDecodeError:
        raise json.JSONDecodeError("Hay un error con el archivo organizer.txt")
    except FileNotFoundError:
        raise FileNotFoundError("El archivo organizer.txt no existe")
    
    #construimos la query
    query=[]
    Labels=[]
    for lb in organizer:
        Labels.append(f"-label:{lb}") #los mensajes que ya tienen una etiqueta presente en el organizer se considera que ya esta clasificado
        for kw in organizer[lb]["keywords"]:
             query.append(f"subject:{kw}")
        for n in organizer[lb]["remitentes"]: #remitentes especificados en organizer
            query.append(f"from:{n}")
            query.append(f"to:{n}")#también filtramos los mensjaes tales que los destinatarios són los remitentes especificados, para detectar conversaciones bidireccionales
        for x in organizer[lb]["destinatarios"]: #destinatarios especificados en organizer
            query.append(f"to:{x}")

    query=" OR ".join(query)
    Labels=" ".join(Labels)
    q=f"-is:starred {Labels} {{{query}}}" #se ignoran los mensajes destacados

    #obtenemos la lista de mensajes y etiquetas
    if Unitats.afegir(6):
        llista_missatges = msg.list(userId=user,q=q).execute()
        llista_labels = lbls.list(userId=user).execute()
    else:
        raise QuoataAssolida ("Se ha alcanzado la quota de unidades por minuto.")

    total=llista_missatges["resultSizeEstimate"]
    if total == 0:
        raise NoMessagesFound("No hay mensajes que respondan a la query.")

    #Creamos las etiquetas de organizer en caso de que no existan, y obtenemos sus id's
    for lb in organizer:
        for l in llista_labels["labels"]:
            if l["name"]==lb:
                organizer[lb]["id"]=l["id"]
                break
        if organizer[lb]["id"] is None:
                if Unitats.afegir(5):
                    nova_lbl=lbls.create(userId=user, body={"name": lb}).execute()
                else:
                    raise QuoataAssolida ("Se ha alcanzado la quota de unidades por minuto.")
                organizer[lb]["id"]=nova_lbl["id"]
                print(f"Se ha creado la etiqueta {lb}")

    cont=0 #es el contador de mensajes procesados
    callback=crear_callback_2(msg,organizer,user)#creamos la función callback para batch

    while True:
        for m in llista_missatges.get("messages", []):
            if cont%50==0:#evitamos asi que el batch contenga demasiadas peticiones a la vez y nos salte rateLimitExceded
                if cont>0:#si hemos procesado más de un mensaje entonces seguro que el batch ya ha sido creado, y podemos ejecutarlo
                    batch.execute(http=cliente._http)
                batch=BatchHttpRequest(batch_uri=cliente._baseUrl + cliente._rootDesc["batchPath"])#creamos el batch para nuestras peticiones de la página actual de mensajes. Especificamos donde tiene que enviar-le las ordenes en la API de gmail
            if Unitats.afegir(20):
                peticio=msg.get(userId=user, id=m["id"], format="metadata", metadataHeaders=["Subject", "From", "To"])
                cont+=1
            else:
                raise QuoataAssolida ("Se ha alcanzado la quota de unidades por minuto.")
            batch.add(peticio,callback=callback)
        batch.execute(http=cliente._http) #ejecutamos la primera pagina de peticiones   
        TokenPagina = llista_missatges.get("nextPageToken") #control de pagina
        print(f"\rMensajes: {cont}")

        if TokenPagina is None:
            break
        if Unitats.afegir(5):
            llista_missatges=msg.list(userId=user, pageToken=TokenPagina,q=q).execute()
        else:
            print(f"\nMissatges porcessats:{cont}")
            raise QuoataAssolida ("Se ha alcanzado la quota de unidades por minuto.")
        print(f"\rUnidades: {Unitats.unitats}")
    print(f"Total mensajes procesados:{cont}")

def crear_callback_2(msg, organizer, user):
    #función que crea el callback para el batch de etiquetaje 
    def callback (request_id, response, exception):
        if exception is not None: 
            if Unitats.unitats>=6000:
                raise QuoataAssolida ("Se ha alcanzado la quota por minuto")
            elif isinstance(exception,HttpError):
                error = json.loads(exception.content)
                reason=error.get("error", {}).get("errors", [{}])[0].get("reason")
                if reason == "rateLimitExceeded":
                    return 
                else:
                    raise HttpError (f"Atencion {error}")
            else:
                raise Exception (f"{exception} en la peticion {request_id} del batch")

        label_ids_to_add=set()#lugar en el almacenamos las id's de las etiquetas que queremos añadir al mensaje. No queremos duplicados asi que lo hacemos en un set

        #inicializamos las variables que contienen el asunto, el remitente y el destinatario del mensaje para evitar problemas. En caso de que no tengan, sencillamente no entraran dentro del for respectivo
        asunto=""
        remitente=""
        destinatario=""

        label_ids=response.get("labelIds",[]) #id's del mensaje. Si no teiene devolvemos una lista vacia

        for head in response["payload"]["headers"]:#almacenamos los valores de los headers que nos interessan del mensaje
            if head["name"] == "Subject":
                asunto = head["value"]
            elif head["name"] == "From":
                remitente = head["value"]
            elif head["name"] == "To":
                destinatario = head["value"]

        paraules=asunto.lower().split()

        for lb in organizer: #etiquetaje 
            for kw in organizer[lb]["keywords"]: #respecto el Subject  
                if " " in kw:
                    if kw.lower() in asunto.lower() and organizer[lb]["id"] not in label_ids:
                        label_ids_to_add.add(organizer[lb]["id"])
                else:
                    if kw.lower() in paraules and organizer[lb]["id"] not in label_ids:
                        label_ids_to_add.add(organizer[lb]["id"])
            for sd in organizer[lb]["remitentes"]: #respecto el remitente
                if sd in remitente and organizer[lb]["id"] not in label_ids:
                    label_ids_to_add.add(organizer[lb]["id"])
                if sd in destinatario and organizer[lb]["id"] not in label_ids:#hacemos la filtración propia también con los destinatarios
                    label_ids_to_add.add(organizer[lb]["id"])
            for rm in organizer[lb]["destinatarios"]: #respcto los destinatarios
                if rm in destinatario and organizer[lb]["id"] not in label_ids:
                     label_ids_to_add.add(organizer[lb]["id"])
        if label_ids_to_add: #añadimos las etiquetas pertinentes
            if Unitats.afegir(5):
                label_ids_to_add = list(label_ids_to_add)
                msg.modify(
                    userId=user, 
                    id=response["id"],
                    body={
                        "addLabelIds": label_ids_to_add,
                        "removeLabelIds": ["INBOX"]
                        }
                    ).execute()
            else:
                raise QuoataAssolida ("El batch superaria la quota per minuto.")
    return callback

def rmv_label(lbls,lbl_name, msg, user="me", remitent=None):

    if remitent is not None:
        query=f"from:{remitent}"
    else:
        query=""
    q=f"-is:starred label:{lbl_name} {{{query}}}" #creamos la query que nos devuelva los mensajes con la etiqueta especificada y el remitente especificado. Evitamos los destacados
    
    if Unitats.afegir(6):
        llista_missatges = msg.list(userId=user,q=q).execute()
        llista_labels = lbls.list(userId=user).execute()
    else:
        raise QuoataAssolida ("Se ha alcanzado la quota de unidades por minuto.")

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
            if Unitats.afegir(5):
                msg.modify(
                    userId=user, 
                    id=m["id"],
                    body={
                        "removeLabelIds": [lbl_id]
                        }
                    ).execute()
            else:
                print(f"Se ha alcanzado la quota de unidades por minuto. Espera antes de volver a aplicar la funcion. Porcesados: {cont}.")
                return
            cont+=1        
        TokenPagina = llista_missatges.get("nextPageToken") #control de pagina

        print(f"\rMensajes: {cont}")

        if TokenPagina is None:
            break
        if Unitats.afegir(5):
            llista_missatges=msg.list(userId=user, pageToken=TokenPagina,q=q).execute()
        else:
            print(f"Se ha alcanzado la quota de unidades por minuto. Espera antes de volver a aplicar la funcion. Porcesados: {cont}.")
            return
        print(f"\rUnidades: {Unitats.unitats}")
    print(f"Total mensajes procesados: {cont}")

def safata_entrada_scan(msg, user="me"):
    if Unitats.afegir(5):
        llista_missatges = msg.list(userId=user,q="label:INBOX").execute()#obtenemos lista mensajes que esten en la bandeja entrada
    else:
        raise QuoataAssolida ("Se ha alcanzado la quota de unidades por minuto.")

    total=llista_missatges["resultSizeEstimate"]
    if total == 0:
        raise NoMessagesFound("No hay mensajes que respondan a la query.")
    cont=0

    while True:#quitamos la etiqueta bandeja entrada
        for m in llista_missatges.get("messages", []):
            if Unitats.afegir(20):
                a=msg.get(userId=user, id=m["id"], format="metadata", metadataHeaders=["Subject", "From"]).execute()
            else: 
                print(f"Se ha alcanzado la quota de unidades por minuto. Espera antes de volver a aplicar la funcion. Porcesados: {cont}.")
                return
            try:
                for lb in  a["labelIds"]:#escanemos etiqueta INBOX
                    if lb !="INBOX":
                        if Unitats.afegir(5):
                            msg.modify(
                                userId=user, 
                                id=m["id"],
                                body={
                                    "removeLabelIds": ["INBOX"]
                                    }
                                ).execute()
                        else:
                            print(f"Se ha alcanzado la quota de unidades por minuto. Espera antes de volver a aplicar la funcion. Porcesados: {cont}.")
                            return
                        break
            except KeyError as e:
                 print(f"Atencion, KeyError:{e}. El mensaje {m["id"]} no tiene el contenedor de labelIds. Se ha omitido") 

            cont+=1
        TokenPagina = llista_missatges.get("nextPageToken") #control de pagina
        print(f"\rMensajes: {cont}")
        if TokenPagina is None:
            break
        if Unitats.afegir(5):
            llista_missatges=msg.list(userId=user, pageToken=TokenPagina,q="label:INBOX").execute()
        else:
            print(f"Se ha alcanzado la quota de unidades por minuto. Espera antes de volver a aplicar la funcion. Porcesados: {cont}.")
            return
        print(f"\rUnidades: {Unitats.unitats}")
    print(f"Total mensajes procesados:{cont}")

#ENVIAR MENSAJES A LA PAPELERA
def marcar_brossa (msg,lbls, user="me"):
    try:#obtenemos de paperera.txt y whitelist.txt los diccionarios que nos permiten clasificar mensajes como correo basura y mensajes exemptos de ser considerados, respectivamente
        with open("paperera.txt", "r", encoding="utf-8") as f: 
            paperera=json.load(f)
        with open("whitelist.txt", "r", encoding="utf-8") as ff: 
            whitelist=json.load(ff)
    except json.JSONDecodeError:
        raise json.JSONDecodeError("Hay algun error con los archivos paperera.txt y whitelist.txt")
    except FileNotFoundError:
        raise FileNotFoundError("Alguno de los archivos requeridos no existe (paperera.txt, whitelist.txt)")

    #construimos la query segun paperera.txt e ignorando los de whitelist.txt
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
    q=f"-is:starred -label:Papelera {queryW} {{{query}}}" #obviamos los mensajes destacados

    #lista de mensajes y etquetas segun la query
    if Unitats.afegir(6):
        llista_missatges = msg.list(userId=user,q=q).execute()
        llista_labels = lbls.list(userId=user).execute()
    else:
        raise QuoataAssolida ("Se ha alcanzado la quota de unidades por minuto.")

    total=llista_missatges["resultSizeEstimate"]
    if total == 0:
        raise NoMessagesFound("No hay mensajes que respondan a la query.")

    #si la etiqueta Papelera no existe la creamos, si existe obtenemos su id
    Check=1
    for l in llista_labels["labels"]:
        if l["name"]=="Papelera":
            etiqueta_brossa=l
            Check=0
            break
    if Check:
        if Unitats.afegir(5):
            etiqueta_brossa=lbls.create(userId=user, body={"name": "Brossa"}).execute()#guardamos el resultado para obtener la id 
        else:
            raise QuoataAssolida ("Se ha alcanzado la quota de unidades por minuto.")
        print(f"Se ha creado la etiqueta Papelera")
    cont=0

    while True: #los mensajes seleccionados los enviamos a la papelera
        for m in llista_missatges.get("messages",[]):
            if Unitats.afegir(5):
                msg.modify(userId=user, id=m["id"],body={"addLabelIds": [etiqueta_brossa["id"]]}).execute()
            else:
                print(f"Se ha alcanzado la quota de unidades por minuto. Espera antes de volver a aplicar la funcion. Porcesados: {cont}.")
                return
            cont+=1

        TokenPagina = llista_missatges.get("nextPageToken") #control de pagina
        print(f"\rMensajes: {cont}")
        if TokenPagina is None:
            break
        if Unitats.afegir(5):
            llista_missatges=msg.list(userId=user, pageToken=TokenPagina,q=q).execute()
        else:
            print(f"Se ha alcanzado la quota de unidades por minuto. Espera antes de volver a aplicar la funcion. Porcesados: {cont}.")
            return
        print(f"\rUnidades: {Unitats.unitats}")
    print(f"\nTotal mensajes: {cont}")

def enviar_brossa(msg, user="me"):
    #función complementaria a marcar_brossa
    
    q="label:Papelera"
    if Unitats.afegir(5):
        llista_missatges = msg.list(userId=user,q=q).execute() #lista mensajes con la etiqueta Papelera
    else:
        raise QuoataAssolida("Se ha alcanzado la quota de unidades por minuto.")
    total=llista_missatges["resultSizeEstimate"]
    if total == 0:
        raise NoMessagesFound("No hay mensajes que respondan a la query.")
    
    cont=0
    while True: #se aplica trash() a los mensajes de dentro la etiqueta 
        for m in llista_missatges.get("messages", []):
            if Unitats.afegir(20):
                msg.trash(userId=user,id=m["id"]).execute()
            else:
                print(f"Se ha alcanzado la quota de unidades por minuto. Espera antes de volver a aplicar la funcion. Porcesados: {cont}.")
                return
            cont+=1
        TokenPagina = llista_missatges.get("nextPageToken") #control de pagina
        print(f"\rMensajes: {cont}")
        if TokenPagina is None:
            break
        if Unitats.afegir(5):
            llista_missatges=msg.list(userId=user, pageToken=TokenPagina,q="label:INBOX").execute()
        else:
            print(f"Se ha alcanzado la quota de unidades por minuto. Espera antes de volver a aplicar la funcion. Porcesados: {cont}.")
            return
        print(f"\rUnidades: {Unitats.unitats}")
    print(f"Total mensajes procesados:{cont}")

#FUNICIÓN PARA CAMBIAR DE USUARIO
def reset_user ():
    if os.path.exists("Token.json"):
        os.remove("Token.json")
        print("Se ha eliminado Token.json. Inicia la sesión con otro usuario autorizado")
    credentials=get_credentials()
    return credentials

#FUNCIÓN PARA REINICIAR BIEN EL CONTADOR DE UNIDADES
def contador ():#esta función pone el programa en pausa el tiempo suficiente como para poder usar el parametro unitats de Unitats como contador para la quota por minuto por usuario (en caso de que el programa no forme parte de un proyecto más grande en google cloud). Para operaciones que se preve que tarden bastante menos de medio minuto no es necesario usarlo debido a que el tiempo que el programa permanecerà parado sera sustancialmente mayor al que tardara en ejecutarse
    Unitats.times()
    print(f"Pausant per {int(Unitats.t1-Unitats.t0+1)}s")
    time.sleep(Unitats.t1-Unitats.t0+1)
    

print("Para poder controlar bien el marcador de unidades, se debe ejecutar la funcion contador al final del codigo")


if __name__=="__main__":
    credentials=get_credentials()
    cliente=cliente_gmail(credentials)
    msg,lbls=recursos(cliente)

    etiquetar(msg,lbls)
    marcar_brossa(msg, lbls)
    enviar_brossa(msg)
    etiquetar(cliente,msg, lbls)

    contador()
    


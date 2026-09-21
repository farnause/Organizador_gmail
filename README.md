## Objectivo
Crear un programa que permita etiquetar y enviar a la papelera mensajes recividos a tu correo gmail, a partir de su remitente, destinatario o ciertas palabras clave en el sujeto del mensaje.

## Como funciona
La idea es establecer comuniación con la API de gmail a través de un proyecto de Google Cloud. Se ha configurado un cliente OAuth para que gmail reconozca mi programa como autorizado, a través del archivo credencials.json.
Una vez se consiguen las credenciales, y se tienen acceso a los recursos del cliente, se pueden obtener listas de mensjaes a través de una query para hacer una primera selección de los mensajes de tu correo, y luego se procede a el etiquetaje o clasifiacióon pertinente de los correos seleccionados.
Este funcionamiento es común en la mayoria de funciones existentes en main.py.

## Descripción
- **get_credentials**:
Función que usa el archivo credentials.json y los SCOPES especificados para autorizar a nuestro programa a enviar peticiones a la API de gmail con un usuario autorizado. La primera vez que se autoriza el programa, se crea un Token.json que permite autorizar automaticamente el programa en futuras ejecuciones, sin necesidad de abrir el navegador.
- **cliente_gmail y recursos**:
Son dos funciones complementarias. La primera crea el cliente de la API de gmail, y la segunda habilita que podamos acceder a los mensajes del usuario autorizado y a sus etiquetas de gmail.
- **get_msg**:
Función que te permite acceder a un coreo especifico a través de su id
- **etiquetar y crear_callback_2**:
Etiquetar es la función que etiqueta todos tus mensajes según el remitente, el destinatario y ciertas palabras o frases del sujeto del mensaje. Primero lee el contenido de organizer.txt y lo convierte a un diccionario. A partir de ese diccionario se hace una query de mensajes al gmail para obtener una lista de mensajes suceptibles a ser etiquetados segun nuestros parámetros. Todos los remitentes especificados en la lista de remitentes de organizer, también contaran automaticamente como destinatarios, para detectar conversaciones bidireccionales y evitar duplicados entre las listas de remitentes y destinatarios de organizer. Una vez hecha la query, se almacenan los mensajes obtenidos en una lista. Utilizamos un while para movernos a través de las paginas de esa lista hasta llegar al final.
Etiquetar es la única función que utiliza batch, por lo que se ha limitado la cantidad de peticiones simultaneas que puede almecenar cada batch a 50, para evitar errores.
crea_callback_2 simplemente crea la función callback que necesita batch.execute, y es donde se hace el etiquetaje de cada mensaje.
-**rmv_label**:



En todas las querys que se hacen en la función, se ignoran los mensajes marcados como destacados, para dejarlos al margen de cualquier clasificación

## Requisitos

## Comentarios personales respecto el programa 

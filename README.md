# Objectivo
Crear un programa que permita etiquetar y enviar a la papelera mensajes recividos a tu correo gmail, a partir de su remitente, destinatario o ciertas palabras clave en el sujeto del mensaje.

# Como funciona
La idea es establecer comuniación con la API de gmail a través de un proyecto de Google Cloud. Se ha configurado un cliente OAuth para que gmail reconozca mi programa como autorizado, a través del archivo credencials.json.  

Una vez se consiguen las credenciales, y se tienen acceso a los recursos del cliente, se pueden obtener listas de mensjaes a través de una query para hacer una primera selección de los mensajes de tu correo, y luego se procede a el etiquetaje o clasifiacióon pertinente de los correos seleccionados.
Este funcionamiento es común en la mayoria de funciones existentes en main.py.

# Descripción
- **Unitats**:
Objecto de la classe UnitatsUsades, pensado para controlar las unidades por minuito que estamos consumiendo con peticiones a la API. El parámetro interno LIMIT represena el limite por minuto especificado por el propio gmail, y tiene un valor de 6000. Como parámetros internos tiene unitats, t0 y t1. El parametro unitats almacena las unidades totales consumidas en la ectual ejecución del programa. Tanto t0 y t1 estan pensadas para controlar el tiempo des de la primera petición a la API, es decir cuando unitats=0, a la última petición a la API. La classe UnitatsUsades contiene dos métodos, afegi y times. El primero va almacenando las unidades consumidas en unitats, reiniciando su valor en caso de haver pasado un minuto, y devuelve 0 cuando hemos sobrepassado 6000 unidades por minuto en la actual ejecución del programa. El método times por otro lado, imprime el valor actual de unitats, y el tiempo pasado entre la primera petición (unitats=0) y la última petición.
- **get_credentials**:
Función que usa el archivo credentials.json y los SCOPES especificados para autorizar a nuestro programa a enviar peticiones a la API de gmail con un usuario autorizado. La primera vez que se autoriza el programa, se crea un Token.json que permite autorizar automaticamente el programa en futuras ejecuciones, sin necesidad de abrir el navegador.
- **cliente_gmail y recursos**:
Son dos funciones complementarias. La primera crea el cliente de la API de gmail, y la segunda habilita que podamos acceder a los mensajes del usuario autorizado y a sus etiquetas de gmail.

- **get_msg**:
Función que te permite acceder a un coreo especifico a través de su id.
- **etiquetar y crear_callback_2**:
Etiquetar es la función que etiqueta todos tus mensajes según el remitente, el destinatario y ciertas palabras o frases del sujeto del mensaje. Primero lee el contenido de organizer.txt y lo convierte a un diccionario. A partir de ese diccionario se hace una query de mensajes al gmail para obtener una lista de mensajes suceptibles a ser etiquetados segun nuestros parámetros. Todos los remitentes especificados en la lista de remitentes de organizer, también contaran automaticamente como destinatarios, para detectar conversaciones bidireccionales y evitar duplicados entre las listas de remitentes y destinatarios de organizer. Una vez hecha la query, se almacenan los mensajes obtenidos en una lista. Utilizamos un while para movernos a través de las paginas de esa lista hasta llegar al final.
Etiquetar es la única función que utiliza batch, por lo que se ha limitado la cantidad de peticiones simultaneas que puede almecenar cada batch a 50, para evitar errores.
crea_callback_2 simplemente crea la función callback que necesita batch.execute, y es donde se hace el etiquetaje de cada mensaje.
- **rmv_label**:
Elimina una etiqueta de todos los mensajes del correo que tengan una etiqueta especificada. Se puede especificar el remitente dando valor a la variable "remitent". Se limita a como máximo todos los mensajes de una etiqueta en vez de todos los mensajes del correo para reducir el riesgo de sobrepasar el limite de 6000 unidades por minuto de gmail.
- **safata_entrada_scan**:
Elimina la etiqueta "INBOX" de los mensajes de la bandeja de entrada.
- **marcar_brossa i enviar_brossa**:
Dos funciones complementarias destinadas a eliminar correos no deseados. marcar_brossa etiqueta los mensajes de ciertos remitentes o con ciertas palabras en el sujeto, con la etiqueta "Papelera" (creandola en caso de que no exista). Luego enviar_brossa manda los mensajes con dicha etiqueta a la basura. Este sistema esta pensado para poder revisar que mensajes que estamos enviando a la basura antes de realmente eliminarlos, si asi se desea.

- **reset_user**:
Función que elimina el archivo "Token.json" en caso de que exista, y vuelve a crearlo con las nuevas credenciales. A parte devuelve las nuevas credenciales. Cabe destacar que antes de ejecutar esta función, se debe proporcionar un nuevo archivo de credentials.json para el nuevo usuario a autorizar, ya que si no reset_user vuelve a autorizar al mismo usuario que ya estaba autorizado.

- **contador**:
Función pensada para ejecutarse al final del codigo en el que se este trabajando. Simplemente ejecuta el métoddo times de Unitats para obtener el tiempo que falta para que se reincie el valor de unitats. Eso es relevante de cara a varias ejecuciones sucesivas del programa, ya que el valor de unitats no se traslada de ejecución a ejecución, perdiendo el control de las unidades consumidas por minuto. Por eso contador para el programa hasta que entre la primera petición y el final de la ejecución del programa pase 1 min. Por ese motivo esta función solo se recomienda ponerla en caso de ejecutar una o más funciones que hagan una cantidad sustancial de peticiones.

## Observaciones
* En todas las querys que se hacen en las funciones, se ignoran los mensajes marcados como destacados, para dejarlos al margen de cualquier clasificación
* Debido a como esta pensado el etiquetaje a partir de organizer, los mensajes que uno se ha enviado a si mismo no se clasificaran nunca, a no ser que se busquen ciertas palabras clave en el sujeto de estos mensajes que se sepa que dichos mensajes contengan.

# Requisitos

A parte de las versiones de los paquetes especificadas en requirements.txt, también es necesario poner en el directorio del programa el archivo credentials.json que uno obtiene al configurar su cliente OAuth.

# Comentarios personales respecto el programa

El objetivo personal con este programa era poder entender bien el concepto de API, y el de cliente de API, y la estructura básica que debe tener un programa que se comunique con una API. Mientras que la funcionalidad de este programa es la misma que la barra buscador que el propio correo de gmail incorpora, me ha permitido conseguir lo que buscava entender respecto mis objetivos. 
Además me ha permitido sentirme un poco más comodo con la programación orientada a objetos, cosa necesaria debido a que la mayor parte de mi experiencia en programación proviene de programar en C. 
Por último, destacar que con este programa me he dado cuenta de ciertos aspectos que puedo mejorar, ya sea con un mejor control de los errores, o incluso un control más consistente de estos errores, y tamién una mejor organización en funciones del codigo para evitar funciones kilometricas. 

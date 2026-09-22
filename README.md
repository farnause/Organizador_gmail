# Objectivo
Crear un programa que permita etiquetar y enviar a la papelera mensajes recibidos a tu correo de Gmail, a partir de su remitente, destinatario o ciertas palabras clave en el sujeto del mensaje.

# Cómo funciona
La idea es establecer comunicación con la API de Gmail mediante un proyecto de Google Cloud. Para ello se ha configurado un cliente OAuth para que Gmail reconozca mi programa como autorizado y solicite al usuario autorización para acceder a su cuenta de Gmail. La configuración del cliente OAuth se guarda en el archivo `credentials.json`.  
Una vez completado el proceso de autenticación, se obtienen los permisos necesarios especificados en `SCOPES`, para poder interactuar con la API de Gmail (que posteriormente se guardarán en `Token.json`), y podemos conseguir los recursos que queremos como cliente.   
Una vez obtenidos los recursos que queremos (en nuestro caso, mensajes y etiquetas), se pueden obtener listas de mensajes a través de una query a Gmail, para hacer una primera selección de los mensajes del correo del usuario, y luego se procede al etiquetaje o clasificación pertinente de los correos seleccionados.  

Este funcionamiento es común en la mayoría de funciones existentes en main.py.

# Descripción
- **Unitats**:
Objeto de la clase `UnitatsUsades`, pensado para controlar las unidades de cuota por minuto que estamos consumiendo, que viene a ser como un sistema de coste ponderado de las peticiones a la API. El parámetro interno LIMIT representa el límite por minuto y por usuario especificado por el propio Gmail, y tiene un valor de 6000.  
Como parámetros internos tiene `unitats`, `t0` y `t1`. El parámetro `unitats` almacena las unidades totales consumidas en la actual ejecución del programa. Tanto `t0` como `t1` están pensadas para controlar el tiempo desde la primera petición a la API, es decir, cuando `unitats=0`, hasta la última petición a la API.  
La clase `UnitatsUsades` contiene dos métodos, `afegir` y `times`. El primero va almacenando las unidades consumidas en `unitats`, reiniciando su valor en caso de haber pasado un minuto, y devuelve 0 cuando hemos sobrepasado 6000 unidades por minuto en la actual ejecución del programa.  
El método `times` por otro lado, imprime el valor actual de `unitats`, y el tiempo pasado entre la primera petición (`unitats=0`) y la última petición.
- **get_credentials**:
Función que usa el archivo `credentials.json` y los `SCOPES` especificados para identificar a nuestro programa y conseguir los permisos para poder enviar peticiones a la API de Gmail con un usuario autorizado. La primera vez que se autoriza el programa, se crea un `Token.json` que permite autorizar automáticamente el programa en futuras ejecuciones, sin necesidad de abrir el navegador.  

Argumentos: No

- **cliente_gmail y recursos**:
Son dos funciones complementarias. La primera crea un objeto cliente para poder interactuar con la API de Gmail con las credenciales proporcionadas, y la segunda habilita que podamos acceder a los recursos que queremos pedir a Gmail a través del cliente.  

Argumentos: respectivamente, `credentials`: objeto creado por `get_credentials` que autorizará a nuestro cliente a interactuar con la API de Gmail y obtener información de nuestra cuenta, `cliente`: objeto que permite la interacción con Gmail.

- **get_msg**:
Función que te permite acceder a un correo específico a través de su id.  

Argumentos: `msg`: objeto de acceso al recurso `messages`, `ID`: id del mensaje, `user`: usuario autorizado. Por defecto es igual a `"me"`, es decir, el usuario que ha sido autorizado por `credentials.json`.  

- **etiquetar y crear_callback_2**:
`etiquetar` es la función que etiqueta todos tus mensajes según el remitente, el destinatario y ciertas palabras o frases del sujeto del mensaje. Primero lee el contenido de `organizer.txt` y lo convierte a un diccionario. A partir de ese diccionario, se hace una query de mensajes al Gmail para obtener una lista de mensajes susceptibles de ser etiquetados según nuestros parámetros. En caso de que en `organizer.txt` esté especificada una etiqueta que no ha sido creada, la crea.  
Todos los remitentes especificados en la lista de remitentes de organizer, también contarán automáticamente como destinatarios, para detectar conversaciones bidireccionales y evitar duplicados entre las listas de remitentes y destinatarios de organizer. Una vez hecha la query, se almacenan los mensajes obtenidos en una lista. Utilizamos un while para movernos a través de las páginas de esa lista hasta llegar al final.  
Etiquetar es la única función que utiliza batch, por lo que se ha limitado la cantidad de peticiones simultáneas que puede almacenar cada batch a 50, para evitar errores.  
`crea_callback_2` simplemente crea la función callback que necesita `batch.execute`, y es donde se hace el etiquetaje de cada mensaje.  

Argumentos (de `etiquetar`): `cliente`, `msg`, `lbls`: objeto de acceso al recurso `labels`, `user`: por defecto `"me"`

- **rmv_label**:
Elimina una etiqueta de todos los mensajes del correo que tengan una etiqueta especificada. Se puede especificar el remitente dando valor a la variable `remitent`. Se limita a como máximo todos los mensajes de una etiqueta en vez de todos los mensajes del correo para reducir el riesgo de sobrepasar el límite de 6000 unidades por minuto de Gmail.  

Argumentos: `lbls`, `lbl_name`: variable que contiene una string, `msg`, `user`: por defecto `"me"`, `remitent`: por defecto `None`

- **safata_entrada_scan**:
Elimina la etiqueta `INBOX` de los mensajes de la bandeja de entrada.  

Argumentos: `msg`, `user`: por defecto `"me"`

- **marcar_brossa i enviar_brossa**:
Dos funciones complementarias destinadas a eliminar correos no deseados. `marcar_brossa` etiqueta los mensajes de ciertos remitentes o con ciertas palabras en el sujeto, con la etiqueta `Papelera` (creándola en caso de que no exista). Luego `enviar_brossa` manda los mensajes con dicha etiqueta a la basura. Este sistema está pensado para poder revisar qué mensajes qué estamos enviando a la basura antes de realmente eliminarlos, si así se desea.

Argumentos: `msg`, `lbls`, `user`: por defecto `"me"` (`enviar_brossa` nonecesita `lbls`)

- **reset_user**:
Función que elimina el archivo `Token.json` en caso de que exista, y vuelve a crearlo con las nuevas credenciales. Aparte, devuelve un objeto `credenciales` para sustituir al anterior. Cabe destacar que antes de ejecutar esta función, se debe proporcionar un nuevo archivo de credentials.json para el nuevo usuario a autorizar, ya que si no, `reset_user`, vuelve a autorizar al mismo usuario que ya estaba autorizado.  

Argumentos: No

- **contador**:
Función pensada para ejecutarse al final del código en el que se esté trabajando. Simplemente ejecuta el método `times` de `Unitats` para obtener el tiempo que falta para que se reinicie el valor de `unitats`. Eso es relevante de cara a varias ejecuciones sucesivas del programa, ya que el valor de unitats no se traslada de ejecución a ejecución, perdiendo el control de las unidades consumidas por minuto. Por eso, `contador` para el programa hasta que, entre la primera petición y el final de la ejecución del programa, pase 1 min.  

Argumentos: No

## Observaciones
* En todas las queries que se hacen en las funciones, se ignoran los mensajes marcados como destacados, para dejarlos al margen de cualquier clasificación.
* Debido a cómo está pensado el etiquetaje a partir de organizer, los mensajes que uno se ha enviado a sí mismo no se clasificarán nunca, a no ser que se busquen ciertas palabras clave en el sujeto de estos mensajes que se sepa que dichos mensajes contienen.
* El hecho de tener que usar `contador` crea la desventaja de que, como mínimo, el cada ejecución del programa dure 1 min, cosa que puede ser molesta en caso de querer hacer una ejecución con muy pocas peticiones. En esos casos, el uso de `contador` podría ser opcional. 

# Requisitos

Aparte de las versiones de los paquetes especificadas en `requirements.txt`, también es necesario poner en el directorio del programa el archivo `credentials.json` que uno obtiene al configurar su cliente OAuth.

# Comentarios personales respecto el programa

El objetivo personal con este programa era poder entender bien el concepto de API, y el de cliente de API, y la estructura básica que debe tener un programa que se comunique con una API. Mientras que la funcionalidad de este programa es la misma que la barra buscador que el propio correo de Gmail incorpora, me ha permitido conseguir lo que buscaba entender respecto a mis objetivos.   
Además, me ha permitido sentirme un poco más cómodo con la programación orientada a objetos, cosa necesaria debido a que la mayor parte de mi experiencia en programación proviene de programar en C.   
Por último, destacar que con este programa me he dado cuenta de ciertos aspectos que puedo mejorar, ya sea con un mejor control de los errores, o incluso un control más consistente de estos errores, y también una mejor organización en funciones del código para evitar duplicación de còdigo y funciones kilométricas. 

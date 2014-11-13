PycoHTTP
========

Super minimal "pico sized" python HTTP server (or API interface)

#Only supports:
* One request at a time, no concurrency
* Only GET requests
* Only responds with text/html
* Does NOT serve files (or anything) by default
* Responses are defined via a Python callback

#Purpouse:
* Adding minimal web interfaces to Python apps.

#Why do this?
* For learning purpouses
* To use in my projects
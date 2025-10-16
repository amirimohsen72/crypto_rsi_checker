# crypto_rsi_checker
check RSI number for crypto from bybit exchange


#env and run
setup venv :
````
python -m venv venv
````

run venv :
````
venv\scripts\activate
````

install packages :
````
pip install -r requirements.txt
````

installed packages list :
````
ccxt , pandas , ta , flask
````

# Separate execution
first run for setup table :
````
python db_setup.py
````
for run rsi_checker use this:
````
python main.py
````
for run web app use this :
````
python app.py
````

# Integrated execution

for run automatic app use this (setup db & fetcher & web page ) :
````
python run.py
````

web page 
```
http://localhost:5000/
```
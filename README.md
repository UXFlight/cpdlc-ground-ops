# Controller-pilot data link communications (CPDLC) - Ground Ops

Research projet @ Polytechnique Montreal made by Missipsa M'Hamed Annane, Srishti Rawal and Philippe Doyon-Poulin. 

This project is meant to simplify and strengthen the communication between the ATC and the Pilot. We used the Global Operational Data Link Document ([GOLD](https://www2023.icao.int/sam/documents/datalink11/gold%201st%20edition_14-jun-10.pdf)), by following the current communication protocol. It is heavily focused on ground operations. It can handle multiple pilots connection (having each one their context), and multiple ATCs, that have a shared context (imagine sharing a doc and both working on it).

The goal is to maximize communication efficiency while keeping a simple of usage interface. This project contains both the Pilot and the ATC interface communicating through one server.

## Fig. 1 : Pilot App
![Pilot Interface](/readme/image.png)

## Fig. 2 : ATC App
![ATC Interface](/readme/image-1.png)

## Tech Used

Pilot Front-End : HTML/ CSS/ JS

ATC Front-End : Angular/ TS/ SCSS

Backend : Flask server with HTTP and WS integration for real-time communication.

Ingescape : To communicate with our flight simulator X-Plane, so we can really simulate the usage of the app on a flight. It works with WS, but they abstract the coding out of it. It is only needed to simulate the whole environment, but can work without it.

Enjoy !

## License

This project is licensed under the [MIT License](./LICENSE.md).  
You’re free to use it, modify it, and share it.  
If you find it useful, or want to contribute, you can always write a message!

# Visualisation
## 1 - Pilot requests the expected taxi clearance
![step 1 - pilot](/readme/image-2.png)

## 2 - ATC receives request and handles it
![step 2 - atc](/readme/image-3.png)

## 3 - Pilot receives ATC response and 'LOADS' the clearances
![step 3 - pilot](/readme/image-4.png)

![step 4 - loading clearance](/readme/image-7.png)

## 4 - In parallel, the ATC can render the clearance on the map, and toggle if they want to see this pilots clearance or not.
![alt text](/readme/image-6.png)
## if you zoom well enough, ATC would see the pilots path
![alt text](/readme/image-5.png)


## Even though it is not usual, the ATC can also initiate a request.
![step X - atc](/readme/image-8.png)

## DISCLAIMER:

- Be aware of the logging system, it will write on a log at every main event [connections, requests, errors, and so on]. Knowing that theres a new connection at each WS client-side [auth is based on sid], this could add up to multiple useless files. 

The logging system is a hidden festure [a true gem] that the client will never perceive. It is such a main service on the backend, as for development, debugging, scalability, abstraction, ... that never sees the light. One global logger is definitely needed. 


## Project Structure

```
.
├── app
│   ├── classes
│   │   ├── agent.py
│   │   ├── airport_cache.py
│   │   ├── apt_parser.py
│   │   ├── atc.py
│   │   ├── clearance.py
│   │   ├── __init__.py
│   │   ├── pilot.py
│   │   ├── socket.py
│   │   └── step.py
│   ├── data
│   │   ├── apt.dat
│   │   ├── CYUL.json
│   │   ├── KDEN.json
│   │   ├── KJFK.json
│   │   ├── KLAX.json
│   │   ├── OEDF.json
│   │   ├── OMDB.json
│   │   ├── OTHH.json
│   │   └── ZSPD.json
│   ├── managers
│   │   ├── airport_map_manager.py
│   │   ├── atc_manager.py
│   │   ├── __init__.py
│   │   ├── log_manager.py
│   │   ├── pilot_manager.py
│   │   ├── socket_manager.py
│   │   └── timer_manager.py
│   ├── routes
│   │   ├── general.py
│   │   └── __init__.py
│   └── utils
│       ├── color.py
│       ├── constants.py
│       ├── __init__.py
│       ├── parse.py
│       ├── simulate_pos.py
│       ├── time_utils.py
│       ├── types.py
│       └── type_validation.py
├── clean.sh
├── client
│   ├── .angular
│   │   └── cache
│   ├── angular.json
│   ├── .gitignore
│   ├── package.json
│   ├── package-lock.json
│   ├── src
│   │   ├── app
│   │   ├── assets
│   │   ├── environments
│   │   ├── favicon.ico
│   │   ├── index.html
│   │   ├── main.ts
│   │   ├── polyfills.ts
│   │   └── styles.scss
│   ├── tsconfig.app.json
│   └── tsconfig.json
├── .gitignore
├── logs
├── main.py
├── project-structure.txt
├── readme
│   ├── image-1.png
│   ├── image-2.png
│   ├── image-3.png
│   ├── image-4.png
│   ├── image-5.png
│   ├── image-6.png
│   ├── image-7.png
│   ├── image-8.png
│   └── image.png
├── README.md
├── requirements.txt
├── run.sh
├── shared
│   └── msg_status.json
├── static
│   ├── assets
│   │   └── pilot.png
│   ├── css
│   │   ├── header.css
│   │   ├── logs.css
│   │   ├── pilot-buttons.css
│   │   ├── request.css
│   │   ├── settings.css
│   │   ├── status.css
│   │   ├── style.css
│   │   └── taxi-clearance.css
│   ├── favicon.ico
│   ├── js
│   │   ├── api
│   │   ├── events
│   │   ├── main.js
│   │   ├── messages
│   │   ├── socket
│   │   ├── socket-events
│   │   ├── state
│   │   ├── text-to-speech.js
│   │   ├── ui
│   │   └── utils
│   └── mp3
│       └── notif.mp3
└── templates
    └── index.html

32 directories, 76 files

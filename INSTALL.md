## Installation and Execution on Linux
**You would need Python 3.8+ and pip, and npm**

1. **Clone repo**

   ```bash
   git clone https://github.com/UXFlight/cpdlc-flask-app.git
   cd cpdlc-flask-app
   ```
#
2. **Create Venv**

   ```bash
   python3 -m venv venv
   cd venv
   source venv/bin/activate
   ```

3. **Install dependencies listed on requirements.txt**

   ```bash
   pip install -r requirements.txt
   ```

4. **Run the app on main.py**

   ```bash
   python3 main.py
   ```

   The pilot interface is available on [http://127.0.0.1:5321/](http://127.0.0.1:5321/)

5. **Change directory on /client**

  ```bash
   cd client
   ```

6. **Install dependencies listed on package.json**

  ```bash
   npm install
   ```

7. **Start client side server**

  ```bash
   npm start
   ```

The ATC interface is available on [http://127.0.0.1:4200/](http://127.0.0.1:4200/)
